---
type: Defect
resource: src/graphrag/ledger.py
title: The newest ledger row was not first
description: "append stamped ts rounded to a millisecond and read sorted with reverse=True. A stable sort keeps the original order inside a tie, so the older row of a tied pair came back first."
tags: [ledger, operations, sorting]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T06:54:11Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T09:35:58Z }
sources:
  - id: ledger
    resource: src/graphrag/ledger.py
  - id: case
    resource: tests/test_watch.py
---

# What was wrong

`append` wrote `round(time.time(), 3)`. A millisecond holds many appends, so rows tied. `read` then
called `sort(key=..., reverse=True)`. Python's sort is stable, and `reverse=True` does not reverse
a tie group: it keeps the original order inside it. So the oldest row of each tie came back first,
under a docstring promising the newest first.[^ledger]

# How it was found

`T-68` rotates the ledger and asks for the newest row by name.[^case] The case named the wrong row,
twice, before the cause was clear.

# What holds it now

The stamp carries full precision. The sort runs ascending and the list is reversed after, which
orders a tie by append order rather than against it. Both changes are needed: precision alone
leaves the stable-sort trap for the next tie.

[^ledger]: `ledger.append` and `ledger.read`.
[^case]: `tests/test_watch.py::test_the_ledger_rotates_and_still_answers`.
