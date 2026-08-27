"""J-08. The caller question, run against both engines and scored.

The routing rule was argued and never graded. `T-91` grades it, and `T-92`
grades the receipt the run has to produce before the number is shown.

`T-91` needs the coderag daemon and this repo's own graph, so it is marked
`engines` and it skips where either is absent. A skip is the honest answer
there. A pass with one arm returning nothing is not.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from graphrag import config, index, store

ROOT = Path(__file__).resolve().parent.parent
ATTESTER = ROOT / "knowledge" / "attesters" / "two_engine_receipt.py"


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


attester = _module(ATTESTER, "two_engine_receipt")
measure_mod = _module(ROOT / "scripts" / "two_engine_measure.py", "two_engine_measure")

SANCTIONED = {
    "test_node_id": measure_mod.NODE_ID,
    "corpus_ref": measure_mod.CORPUS_REF,
}

CONCEPT = ROOT / "knowledge" / "computations" / "the-graph-answers-the-caller-question.md"


def _receipt_on_disk() -> dict:
    """What the sanctioned run wrote, or a skip. A literal here grades itself."""
    path = config.receipt_path(measure_mod.NODE_ID)
    if not path.is_file():
        pytest.skip(f"no receipt at {path}: run the `engines` case first")
    return json.loads(path.read_text(encoding="utf-8"))


def test_a_hung_search_raises_rather_than_scoring_zero(monkeypatch):
    """T-216. A daemon that never answers is the case an error exit misses."""

    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(measure_mod.subprocess, "run", hang)
    with pytest.raises(RuntimeError, match="answered nothing"):
        measure_mod.coderag_files("index", "lexical")


@pytest.mark.engines
def test_the_graph_wins_the_caller_question():
    """T-91. The claim is the ordering and the split, never the three digits.

    A number moves with the corpus, and this corpus is the repo under work. So
    the assertions are the two things the routing rule actually claims: the
    graph beats both semantic arms on a caller question, and it is exact only
    where the name is distinctive.
    """
    reason = measure_mod.arm_unreachable()
    if reason:
        pytest.skip(f"{reason}, so one arm would score zero for the wrong reason")
    measure = measure_mod
    with config.receipt_lock(measure.NODE_ID):
        index.index_once(ROOT)
        conn = store.connect(config.index_path(ROOT), create=False)
        try:
            report = measure.measure(conn)
        finally:
            conn.close()
        # The receipt is written before the assertions, so a run that moves a
        # number leaves the artifact rather than only a red test. It says
        # `unverified` until the assertions below have run over it.
        measure.write_receipt(report)
        _assert_the_graph_wins(report)
        measure.write_receipt(report, measure.PASSED)


def _assert_the_graph_wins(report: dict) -> None:
    measure = measure_mod

    summary = report["summary"]
    # The rule claims the graph beats both arms, and it claims nothing about
    # which arm places second. The two retrieval arms reindex under this test,
    # so an ordering between them reds on a run that moved neither engine.
    assert summary["graphrag"]["f1"] > summary["coderag-lexical"]["f1"]
    assert summary["graphrag"]["f1"] > summary["coderag-semantic"]["f1"]

    # The finding, after `D-19` and then `D-27`. A distinctive name resolves
    # exactly. A colliding one did too once the expression receiver stopped
    # scoring the whole pool, so the split the earlier run measured is closed.
    # The floor and the ceiling are asserted, never the equality: a corpus that
    # holds a receiver the rule cannot place reopens the split honestly.
    distinctive = report["by_class"][measure.DISTINCTIVE]["graphrag"]
    collides = report["by_class"][measure.COLLIDES]["graphrag"]
    assert distinctive["precision"] == 1.0
    assert distinctive["recall"] == 1.0
    assert collides["precision"] > 0.6
    assert collides["precision"] <= distinctive["precision"]

    # The rule refuses a receiver it cannot place, so recall is what proves it
    # refuses no real call. A drop here is the rule eating edges it should keep.
    assert summary["graphrag"]["recall"] == 1.0


@pytest.mark.engines
def test_the_two_engine_receipt_is_attested():
    """T-92. The receipt the run wrote is graded, and a moved number is refused.

    This case held a hand-typed `RECEIPT` with a stale SHA until the audit of
    2026-08-27, so the attester compared the claim against a copy of itself.
    `D-21` had already ruled that out for the sibling computation and this one
    was missed.
    """
    receipt = _receipt_on_disk()
    claim = {name: receipt[name] for name in ("f1_graph", "f1_lexical", "f1_graph_collides")}

    got = attester.attest(sanctioned_computation=SANCTIONED, receipt=receipt, claimed_value=claim)
    assert got["ok"] is True
    assert got["details"]["commit_sha"] == receipt["commit_sha"]

    moved = attester.attest(
        sanctioned_computation=SANCTIONED,
        receipt=receipt,
        claimed_value={**claim, "f1_graph_collides": receipt["f1_graph_collides"] + 0.1},
    )
    assert moved["ok"] is False
    assert "f1_graph_collides" in moved["reason"]

    thin = {k: v for k, v in receipt.items() if k != "f1_graph_collides"}
    dropped = attester.attest(sanctioned_computation=SANCTIONED, receipt=thin, claimed_value=claim)
    assert dropped["ok"] is False
    assert dropped["details"]["missing"] == ["f1_graph_collides"]


@pytest.mark.engines
def test_the_two_engine_receipt_agrees_with_the_concept():
    """T-123. The prose claims digits and nothing compared them to a run.

    Only the graph figures are graded. The two retrieval arms move between runs
    on the same tree, because the coderag index reindexes under them, so a digit
    of theirs held to a receipt would red this concept on any edit. The concept
    reports them as of the run its footnote names, and the footnote is what
    dates them. The sibling rule is `T-111`.
    """
    receipt = _receipt_on_disk()
    text = CONCEPT.read_text(encoding="utf-8")
    assert receipt["corpus_ref"] == measure_mod.CORPUS_REF
    assert f"F1 {receipt['f1_graph']:.3f}" in text
    assert f"F1 is {receipt['f1_graph_collides']:.3f}" in text
    assert f"{receipt['f1_graph_distinctive']:.3f} on precision" in text
    # The commit SHA is not compared. The footnote names the run that measured the
    # digits, and the next commit moves HEAD without moving a number.
