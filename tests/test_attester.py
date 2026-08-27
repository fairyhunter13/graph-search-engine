"""The bundle's attester, graded the only way an attester can be: by failing.

A passing attester nobody has seen fail is not evidence. Every case here moves
one thing about a sound receipt and asserts the verdict turns false with a
reason naming what disagreed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

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
    "commit_sha": "f650204",
    "mean_global": 10.8631,
    "mean_scoped": 1.4902,
    "n_files": 755,
}

CLAIM = {"mean_global": 10.86, "mean_scoped": 1.49, "n_files": 755}


def test_sound_receipt_is_accepted():
    got = attester.attest(sanctioned_computation=SANCTIONED, receipt=RECEIPT, claimed_value=CLAIM)
    assert got["ok"] is True
    assert got["reason"] is None
    assert got["details"]["commit_sha"] == "f650204"
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
    assert got["details"] == {"field": "mean_scoped", "claimed": 1.1, "measured": 1.49}


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
