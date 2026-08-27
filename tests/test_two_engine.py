"""J-08. The caller question, run against both engines and scored.

The routing rule was argued and never graded. `T-91` grades it, and `T-92`
grades the receipt the run has to produce before the number is shown.

`T-91` needs the coderag daemon and this repo's own graph, so it is marked
`engines` and it skips where either is absent. A skip is the honest answer
there. A pass with one arm returning nothing is not.
"""

from __future__ import annotations

import importlib.util
import shutil
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

SANCTIONED = {
    "test_node_id": "tests/test_two_engine.py::test_the_graph_wins_the_caller_question",
    "corpus_ref": "graph-search-engine",
}

RECEIPT = {
    "test_node_id": SANCTIONED["test_node_id"],
    "corpus_ref": "graph-search-engine",
    "commit_sha": "6be17f6",
    "n_questions": 10,
    "f1_graph": 0.743,
    "f1_lexical": 0.569,
    "f1_semantic": 0.383,
    "f1_graph_distinctive": 1.0,
    "f1_graph_collides": 0.538,
}


@pytest.mark.engines
def test_the_graph_wins_the_caller_question():
    """T-91. The claim is the ordering and the split, never the three digits.

    A number moves with the corpus, and this corpus is the repo under work. So
    the assertions are the two things the routing rule actually claims: the
    graph beats both semantic arms on a caller question, and it is exact only
    where the name is distinctive.
    """
    if shutil.which("coderag") is None:
        pytest.skip("no coderag CLI, so one arm would score zero for the wrong reason")
    measure = _module(ROOT / "scripts" / "two_engine_measure.py", "two_engine_measure")
    index.index_once(ROOT)
    conn = store.connect(config.index_path(ROOT), create=False)
    try:
        report = measure.measure(conn)
    finally:
        conn.close()

    summary = report["summary"]
    assert summary["graphrag"]["f1"] > summary["coderag-lexical"]["f1"]
    assert summary["coderag-lexical"]["f1"] > summary["coderag-semantic"]["f1"]

    # The finding. A distinctive name resolves exactly. A name the tree also
    # carries as an attribute does not, because the receiver is discarded.
    distinctive = report["by_class"][measure.DISTINCTIVE]["graphrag"]
    collides = report["by_class"][measure.COLLIDES]["graphrag"]
    assert distinctive["precision"] == 1.0
    assert distinctive["recall"] == 1.0
    assert collides["precision"] < 0.6


def test_the_two_engine_receipt_is_attested():
    """T-92. A sound receipt passes, and a moved number does not."""
    claim = {
        "f1_graph": 0.74,
        "f1_lexical": 0.57,
        "f1_graph_distinctive": 1.0,
        "f1_graph_collides": 0.54,
    }
    got = attester.attest(sanctioned_computation=SANCTIONED, receipt=RECEIPT, claimed_value=claim)
    assert got["ok"] is True
    assert got["details"]["commit_sha"] == "6be17f6"

    moved = attester.attest(
        sanctioned_computation=SANCTIONED,
        receipt=RECEIPT,
        claimed_value={**claim, "f1_graph_collides": 0.95},
    )
    assert moved["ok"] is False
    assert "f1_graph_collides" in moved["reason"]

    thin = {k: v for k, v in RECEIPT.items() if k != "f1_graph_collides"}
    dropped = attester.attest(sanctioned_computation=SANCTIONED, receipt=thin, claimed_value=claim)
    assert dropped["ok"] is False
    assert dropped["details"]["missing"] == ["f1_graph_collides"]
