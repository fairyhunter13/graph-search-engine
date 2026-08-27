"""The bundle's attester, graded the only way an attester can be: by failing.

A passing attester nobody has seen fail is not evidence. Every case here moves
one thing about a sound receipt and asserts the verdict turns false with a
reason naming what disagreed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from graphrag import config
from test_resolve import NODE_ID

ROOT = Path(__file__).resolve().parent.parent
ATTESTER = ROOT / "knowledge" / "attesters" / "measurement_equality.py"


def _load():
    spec = importlib.util.spec_from_file_location("measurement_equality", ATTESTER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


attester = _load()

SANCTIONED = {
    "test_node_id": "tests/test_resolve.py::test_import_scoping_collapses_candidates",
    "corpus_ref": "v3.12.7",
}

RECEIPT = {
    "test_node_id": "tests/test_resolve.py::test_import_scoping_collapses_candidates",
    "corpus_ref": "v3.12.7",
    "commit_sha": "9e4212f",
    "tree_dirty": False,
    "outcome": "pass",
    "mean_global": 10.8576,
    "mean_scoped": 1.2437,
    "n_files": 755,
}

CLAIM = {"mean_global": 10.86, "mean_scoped": 1.24, "n_files": 755}


def test_sound_receipt_is_accepted():
    got = attester.attest(sanctioned_computation=SANCTIONED, receipt=RECEIPT, claimed_value=CLAIM)
    assert got["ok"] is True
    assert got["reason"] is None
    assert got["details"]["commit_sha"] == "9e4212f"
    assert got["details"]["attested"] == ["mean_global", "mean_scoped", "n_files"]


def test_changed_number_is_rejected():
    """The concept moves and the run does not. That is the whole point."""
    got = attester.attest(
        sanctioned_computation=SANCTIONED,
        receipt=RECEIPT,
        claimed_value={**CLAIM, "mean_scoped": 1.10},
    )
    assert got["ok"] is False
    assert "mean_scoped" in got["reason"]
    assert got["details"] == {"field": "mean_scoped", "claimed": 1.1, "measured": 1.24}


def test_a_run_on_a_dirty_tree_is_rejected():
    """The SHA names code that did not run, and no attester can read a tree."""
    got = attester.attest(
        sanctioned_computation=SANCTIONED,
        receipt={**RECEIPT, "tree_dirty": True},
        claimed_value=CLAIM,
    )
    assert got["ok"] is False
    assert got["details"]["tree_dirty"] is True


def test_a_run_whose_assertions_never_ran_is_rejected():
    """A receipt lands before the assertions, so a red run leaves one too."""
    got = attester.attest(
        sanctioned_computation=SANCTIONED,
        receipt={**RECEIPT, "outcome": "unverified"},
        claimed_value=CLAIM,
    )
    assert got["ok"] is False
    assert got["details"]["outcome"] == "unverified"


def test_a_run_against_another_corpus_is_rejected():
    got = attester.attest(
        sanctioned_computation=SANCTIONED,
        receipt={**RECEIPT, "corpus_ref": "v3.13.0"},
        claimed_value=CLAIM,
    )
    assert got["ok"] is False
    assert got["details"]["field"] == "corpus_ref"


def test_a_missing_receipt_field_is_named_rather_than_skipped():
    thin = {k: v for k, v in RECEIPT.items() if k != "commit_sha"}
    got = attester.attest(sanctioned_computation=SANCTIONED, receipt=thin, claimed_value=CLAIM)
    assert got["ok"] is False
    assert got["details"]["missing"] == ["commit_sha"]


def test_a_claim_no_receipt_field_carries_is_refused():
    got = attester.attest(
        sanctioned_computation=SANCTIONED,
        receipt=RECEIPT,
        claimed_value={**CLAIM, "ratio": 7.3},
    )
    assert got["ok"] is False
    assert got["details"]["unknown"] == ["ratio"]


@pytest.mark.parametrize("claim", [{}, {"n_files": 755}])
def test_an_empty_claim_attests_nothing_and_a_partial_one_attests_itself(claim):
    got = attester.attest(sanctioned_computation=SANCTIONED, receipt=RECEIPT, claimed_value=claim)
    assert got["ok"] is bool(claim)


def test_a_second_concurrent_run_refuses_rather_than_clobbers(tmp_path, monkeypatch):
    """The name is a pure function of the node ID, so two runs share one file."""
    monkeypatch.setattr(config, "RECEIPT_DIR", tmp_path)
    with config.receipt_lock(NODE_ID):
        config.write_receipt(NODE_ID, {"test_node_id": NODE_ID})
        with pytest.raises(RuntimeError, match="already holds"):
            with config.receipt_lock(NODE_ID):
                pass
    assert json.loads(config.receipt_path(NODE_ID).read_text(encoding="utf-8")) == {
        "test_node_id": NODE_ID
    }
    # The lock is released, so the next run is not blocked by the last one.
    with config.receipt_lock(NODE_ID):
        pass


def test_the_receipt_on_disk_is_attested():
    """`T-07`'s own receipt, graded. The dicts above are a shape, not a run.

    `D-21` ruled out grading a literal and the fix landed on the sibling
    computation only. `RECEIPT` here still carries `9e4212f`, five commits behind
    HEAD, so the attester compared a claim against a copy of itself.

    Skipped where the receipt is absent, the way the two-engine case is. A
    literal standing in for a run grades itself.
    """
    path = config.receipt_path(NODE_ID)
    if not path.is_file():
        pytest.skip(f"no receipt at {path}: run the `corpus` case first")
    receipt = json.loads(path.read_text(encoding="utf-8"))

    sanctioned = {"test_node_id": NODE_ID, "corpus_ref": config.CORPUS_REF}
    claim = {name: receipt[name] for name in ("mean_global", "mean_scoped", "n_files")}

    got = attester.attest(sanctioned_computation=sanctioned, receipt=receipt, claimed_value=claim)
    assert got["ok"] is True
    assert got["details"]["commit_sha"] == receipt["commit_sha"]

    moved = attester.attest(
        sanctioned_computation=sanctioned,
        receipt=receipt,
        claimed_value={**claim, "mean_scoped": receipt["mean_scoped"] + 0.5},
    )
    assert moved["ok"] is False
    assert "mean_scoped" in moved["reason"]

    thin = {k: v for k, v in receipt.items() if k != "n_files"}
    dropped = attester.attest(sanctioned_computation=sanctioned, receipt=thin, claimed_value=claim)
    assert dropped["ok"] is False
    assert dropped["details"]["missing"] == ["n_files"]
