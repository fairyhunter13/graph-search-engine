---
type: Defect
resource: tests/test_attester.py
title: The attester graded a literal, so the number that moved moved past it
description: "`D-19` moved mean_scoped from 1.49 to 1.24 and one of seven copies was updated. The receipt the attester grades was a hand-written dict in test source, so it went stale with the claim and the two still agreed."
tags: [attestation, measurement, drift]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T09:45:00Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T10:24:21Z }
sources:
  - id: attester-case
    resource: tests/test_attester.py
  - id: measurement
    resource: tests/test_resolve.py
  - id: concept
    resource: knowledge/computations/import-scoping-collapses-the-candidate-set.md
---

# What happened

`D-19` taught the resolver to read a member call's receiver. That moved the scoped mean from 1.49
to 1.24 and scoped ambiguity from 17.7% to 8.9%.[^measurement] One paragraph of
`docs/development-plan.md` was updated. Six other copies were not: the two plan documents, the
computation concept, its index gloss, the `resolve.py` docstring, and the attester case.

# Why nothing caught it

`T-07` asserts bands rather than values, which is right. A corpus at another tag moves both arms
together, so an exact assertion would fail on a change that means nothing. The ratio is the claim
and the ratio held.

That leaves the attester as the only thing comparing a claim against a value. It was comparing two
literals.[^attester-case] `RECEIPT` was a dict in test source, carrying `commit_sha: f650204` from
a run before the receiver landed. `CLAIM` was the concept's numbers, typed again. Both went stale
in the edit that should have moved them. So `attest` returned `ok` on a number no run had produced
in weeks.

# What holds it now

The measurement writes a receipt to disk, and `T-111` grades that file against the claim. A moved
number now fails at the next run rather than at the next audit.

# What would have to be true to revisit this

A second consumer of the same measurement. The receipt is keyed by test node ID, so two sanctioned
runs of one computation would collide on one path.

[^measurement]: `tests/test_resolve.py::test_import_scoping_collapses_candidates`, CPython v3.12.7,
    755 files, 53853 call sites.

[^attester-case]: `tests/test_attester.py::test_sound_receipt_is_accepted` before this change.
