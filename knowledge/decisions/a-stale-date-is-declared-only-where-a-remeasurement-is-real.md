---
type: Decision
resource: knowledge/computations/import-scoping-collapses-the-candidate-set.md
title: A stale date is declared only where a re-measurement date is real
description: "Reachability beats a calendar. The nightly sweep catches a moved page, a rewritten commit and a deleted path, and a date with no owner and no runbook is a scheduled outage."
tags: [okf, freshness, nightly]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T06:15:16Z }
sources:
  - id: nightly
    resource: https://github.com/fairyhunter13/claude-code-workflows
---

# The fleet already solved freshness a different way

A nightly sweep runs the verifiers across every bundle on the machine and never writes a
stamp.[^nightly] Its own comment states the design: a timer that writes the stamp it just earned
leaves nobody having decided anything. What it catches is what a date cannot, namely an upstream
page that moved, a commit rewritten out of a history, and a path deleted under a concept that still
cites it.

# A date with no owner is a scheduled outage

One live stale date exists in the fleet, and it fires four days after this was written. It blocks
every push in that repo on a day nobody chose. That is the failure mode, and it is the argument
against declaring one out of habit.

# So the rule is narrow

Declare a stale date where a re-measurement date is genuine, which here means a number tied to a
pinned corpus. Lean on the nightly for everything else.

# The rule was written and then not applied, 2026-08-27

For a while no concept in the bundle carried a stale date. This record meanwhile said one belonged on
a number tied to a pinned corpus. That is a contradiction the bundle carried against itself. The
resolution is to apply the rule rather than to weaken it.

[The import-scoping computation](../computations/import-scoping-collapses-the-candidate-set.md) is
the sanctioned case. It now carries `stale_after: 2027-08-27T00:00:00Z`. Its corpus is CPython at tag
`v3.12.7`, which is frozen and fetchable. Its procedure is the executor skill. Its receipt names the
test node, so a later run compares against this one. The date therefore has an owner and a runbook,
which is what the rule asks for.

# The second computation is a different case, and it carries no date

[The routing measurement](../computations/the-graph-answers-the-caller-question.md) is pinned to a
commit of this repository. That corpus is the tree under work, so it moves with every commit, and
its ground truth is read by hand.

A calendar date says nothing there. The number is already stale on the next commit that adds a
caller. It is still correct on a day the tree did not move. The real trigger is a commit, and the
receipt plus the commit SHA is what reads it. So that concept keeps no `stale_after`, and the
nightly stays its freshness mechanism.

[^nightly]: `okf-verify-nightly.sh`, which runs the verifiers and never passes the stamp flag.
