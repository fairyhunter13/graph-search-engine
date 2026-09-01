"""Attest a save-to-searchable freshness receipt.

The grader lives in `measurement_equality.py`. This module is the contract:
one receipt shape, one provenance pair, and nothing else. A second contract
needs a second module, because the gate reads one module-level
`RECEIPT_FIELDS` and a union of two shapes would grade neither.

Never uses an LLM. Never makes network calls. Safe to run consumer-side.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _grader():
    """The sibling by path, because an attester is run from anywhere."""
    path = Path(__file__).with_name("measurement_equality.py")
    spec = importlib.util.spec_from_file_location("measurement_equality", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"no grader beside this attester at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


grade = _grader().grade

# Both arms, and the sample count beside them. A p50 alone hides the tail, and
# the tail is where a save waits behind a whole-tree pass. `misses` is a field
# rather than an absence, because a sample that never became queryable is the
# reading that matters most and a dropped row would report it as silence.
RECEIPT_FIELDS = (
    "test_node_id",
    "corpus_ref",
    "commit_sha",
    "tree_dirty",
    "outcome",
    "files",
    "n_samples",
    "misses",
    "edit_to_queryable_ms_p50",
    "edit_to_queryable_ms_p99",
    "whole_tree_pass_s",
)

PROVENANCE_FIELDS = ("test_node_id", "corpus_ref")


def attest(*, sanctioned_computation: dict, receipt: dict, claimed_value: dict) -> dict:
    """Grade one run. Returns `{"ok", "reason", "details"}` and never raises."""
    return grade(
        fields=RECEIPT_FIELDS,
        provenance=PROVENANCE_FIELDS,
        sanctioned_computation=sanctioned_computation,
        receipt=receipt,
        claimed_value=claimed_value,
    )
