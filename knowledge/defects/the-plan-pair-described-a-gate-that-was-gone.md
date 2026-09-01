---
type: Defect
resource: docs/test-plan.md
title: The plan pair described a gate that was gone
description: "docs/test-plan.md and .github/workflows/ci.yml both described a five-check pre-push gate over the plan pair. 832b1bb deleted that block from .githooks/pre-push on 2026-08-29 and neither document moved. Nothing graded the pair for three days: 6 done rows named tests that no longer exist, 4 owned paths named deleted files, 26 tests were written that no row names, and 1 dev row covered nothing. The gate is now tests/test_plan_pair.py, which the suite runs."
tags: [plan-pair, gate, drift, docs]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: gate
    resource: tests/test_plan_pair.py
  - id: hook
    resource: .githooks/pre-push
  - id: plan
    resource: docs/test-plan.md
---

# What happened

`832b1bb`, 2026-08-29, cut every pre-push gate but the OKF arm. The plan-pair block went with
`scripts/check_no_shrink.py`, `check_attester_contract.py` and `check_index_gloss.py`. The hook
says so in its own header[^hook]. `docs/test-plan.md` kept a section describing the five checks it
used to run, and `.github/workflows/ci.yml` opened with a line repeating the claim.

So for three days the plan pair was graded by a paragraph. What that left, measured against
`a4917bf` by running the replacement gate over the documents as they stood[^gate]:

```
rows: 303   dev rows: 55   exempt: 9
6  done rows naming a test that does not exist   T-32 T-48 T-193 T-210 T-214 T-215
4  owned paths naming a deleted file             D-14 D-29 D-31 D-33
26 tests that exist and no row names
1  dev row covering nothing                      D-50
red: 4 of 7 checks
```

Four of the six dead rows point at the same commit that deleted the gate: `T-32`, `T-193` and
`T-210` graded three of the scripts `832b1bb` removed. `T-214` and `T-215` graded the quiet window
`a7a7884` later deleted, and `D-32` still carried that window as `done` — two rows in the pair
asserting opposite facts about the same code. `T-48` was never dead: the test was renamed and
`T-284` already recorded the rename, so the row was a duplicate rather than a corpse.

# The cause, which is not the rows

Every one of these is what an unrun gate leaves behind, and the six rows are the symptom. The
cause is that a check described in prose is a check nobody runs, and deleting the runner left no
mark on either document that described it. The rows did not rot faster after 2026-08-29 — they
rotted at the same rate, and nothing was reading.

The second half is where the gate lived. A pre-push hook is skippable with `--no-verify` and is
installed per clone with `git config core.hooksPath .githooks`, so a machine that never ran that
command never had the gate at all.

# What holds it

`tests/test_plan_pair.py`, seven checks, run by `pytest` and therefore by CI on every push. It
was run against the documents above before they were corrected and read **4 red of 7**, which is
the count in the block. All seven are green against the corrected pair.

The checks read both directions — a row naming an absent test, and a test no row names — because
only the first is a rot and the second is work that was never proposed. Collection is an
`ast.parse` walk over `tests/test_*.py` and not a nested `pytest --collect-only`: 0 of 303 rows
carry a parametrised `[case]` suffix, so real collection would name nothing the walk does not.

The two escape hatches are counted rather than silent. A `(ccw) ` node id is a test in the sibling
repository, and `test_a_foreign_node_is_exempt_and_the_exemption_is_visible` fails when the exempt
count reaches zero — an escape hatch nobody can see the size of is a hole. `(deletion)` in a dev
row's coverage cell is the second, and `D-50` is its only holder.

Six rows moved to `dropped` with one line of reason each, and none was deleted. A contradicted row
keeps its number forever, because a number that can be reissued makes every earlier reference to
it a lie.

# What it does not check, stated so the next audit need not re-derive it

The contract both documents state is *at least one*: every `T-nn` names one `S-nn` and at least
one `D-nn`, every `D-nn` names at least one `T-nn`. The gate holds exactly that. It does not hold
reciprocity — that a `D-nn` a test row names lists that `T-nn` back.

Measured on 2026-09-01: **96** test-to-dev pairs where the dev row does not name the test row back,
and **3** the other way (`D-25`/`T-11`, `D-32`/`T-16`, `D-49`/`T-06`). **81** of the 96 stand at
`a4917bf`, before this gate existed, spread from `T-129` to `T-289` — so a partial coverage cell is
the convention this pair has always been written in, and not drift these commits introduced. A dev
row's coverage cell is a pointer; the test row's `D-nn covered` cell is what carries coverage.

Adding the check would assert a stronger contract than either document states and would land 99
mechanical cell edits with it. That is a plan-pair ruling and not a gate fix, so it is recorded
here rather than taken.

[^hook]: `.githooks/pre-push` — the header naming 2026-08-29 and the three deleted scripts.
[^gate]: `tests/test_plan_pair.py` — the seven checks, run against `git show HEAD:docs/*`.
