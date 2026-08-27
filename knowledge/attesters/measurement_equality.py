"""Attest that a measurement receipt came from the sanctioned computation.

Three checks, and they answer different questions. Integrity asks whether the
run is one anything may be read off. Provenance asks whether the computation
that ran is the one the concept sanctions. Fidelity asks whether the value
about to be displayed is the value the receipt carries.

Never uses an LLM. Never makes network calls. Safe to run consumer-side.
Nothing here raises: every failure path returns a reason and a details map
naming what was compared.
"""

from __future__ import annotations

from typing import Any

# Every field a receipt must carry, and every field this module reads. The
# `D-14` contract check compares a concept's `executor.receipt` against this
# tuple, so a receipt field nothing inspects fails the gate rather than riding
# along unread.
RECEIPT_FIELDS = (
    "test_node_id",
    "corpus_ref",
    "commit_sha",
    "tree_dirty",
    "outcome",
    "mean_global",
    "mean_scoped",
    "n_files",
)

# The fields provenance compares. A commit SHA is recorded and not compared:
# the sanctioned computation outlives the commit that last ran it. What is
# compared is whether the tree matched that SHA, because a dirty tree makes the
# SHA name code that did not run and this module reads no tree.
PROVENANCE_FIELDS = ("test_node_id", "corpus_ref")

# What a receipt says once the assertions have run over it and held. A run
# writes its receipt before them, so a red run leaves numbers on disk too.
PASSED = "pass"

# Two decimal places. A float carries more digits than a measurement means, and
# comparing the raw repr makes an attester fail on a rounding difference that
# changes no claim.
PLACES = 2


def _verdict(ok: bool, reason: str | None, **details: Any) -> dict:
    return {"ok": ok, "reason": reason, "details": details}


def _canonical(value: Any) -> Any:
    """One shape per value, so two spellings of one number compare equal."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), PLACES)
    return str(value).strip()


def attest(*, sanctioned_computation: dict, receipt: dict, claimed_value: dict) -> dict:
    """Grade one run. Returns `{"ok", "reason", "details"}` and never raises."""
    return grade(
        fields=RECEIPT_FIELDS,
        provenance=PROVENANCE_FIELDS,
        sanctioned_computation=sanctioned_computation,
        receipt=receipt,
        claimed_value=claimed_value,
    )


def grade(
    *,
    fields: tuple[str, ...],
    provenance: tuple[str, ...],
    sanctioned_computation: dict,
    receipt: dict,
    claimed_value: dict,
) -> dict:
    """The grader, with the contract passed in.

    A second computation carries a second receipt shape, and one module can
    declare only one `RECEIPT_FIELDS`. So the contract is the parameter and the
    comparison is shared, rather than copied into a second file.
    """
    missing = [f for f in fields if f not in receipt]
    if missing:
        return _verdict(False, f"the receipt omits {', '.join(missing)}", missing=missing)

    if receipt["tree_dirty"]:
        return _verdict(
            False,
            "the run happened on a dirty tree, so its commit_sha names code that did not run",
            commit_sha=_canonical(receipt["commit_sha"]),
            tree_dirty=True,
        )

    outcome = _canonical(receipt["outcome"])
    if outcome != PASSED:
        return _verdict(
            False,
            f"the run recorded outcome={outcome!r}, so nothing asserted over these numbers",
            outcome=outcome,
        )

    for field in provenance:
        if field not in sanctioned_computation:
            return _verdict(False, f"the sanctioned computation omits {field}", field=field)
        want = _canonical(sanctioned_computation[field])
        got = _canonical(receipt[field])
        if want != got:
            return _verdict(
                False,
                f"the run used {field}={got!r} and the sanctioned computation names {want!r}",
                field=field,
                sanctioned=want,
                ran=got,
            )

    unknown = [k for k in claimed_value if k not in fields]
    if unknown:
        return _verdict(
            False,
            f"the claim names {', '.join(unknown)}, which no receipt field carries",
            unknown=unknown,
        )
    if not claimed_value:
        return _verdict(False, "the claim is empty, so there is nothing to attest")

    for field, claimed in claimed_value.items():
        want = _canonical(claimed)
        got = _canonical(receipt[field])
        if want != got:
            return _verdict(
                False,
                f"the concept claims {field}={want!r} and the receipt carries {got!r}",
                field=field,
                claimed=want,
                measured=got,
            )

    return _verdict(
        True,
        None,
        test_node_id=_canonical(receipt["test_node_id"]),
        corpus_ref=_canonical(receipt["corpus_ref"]),
        commit_sha=_canonical(receipt["commit_sha"]),
        attested=sorted(claimed_value),
    )
