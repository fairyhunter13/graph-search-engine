---
type: Defect
resource: src/graphrag/scip/ingest.py
title: The overlay had nothing left to upgrade
description: "`_rewrite_call` upgraded a call site only where a stored `CALLS` edge already sat at that byte. Query-time resolution stopped storing every cross-file call edge, so the SCIP tier could upgrade only same-file calls -- the ones it adds least to."
tags: [scip, resolution, indexing]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: rewrite
    resource: src/graphrag/scip/ingest.py
  - id: case
    resource: tests/test_scip_ingest.py
---

# What broke

`_rewrite_call` read `edges` for a `CALLS` row at the call site byte and returned `False` where
there was none[^rewrite]. That guard is right, and it is what keeps the tier from inventing an edge
out of a name mention. It stopped working the moment a cross-file call became a `refs` row instead
of an edge.

The whole value of the tier is on cross-file calls. A same-file call already scores 0.90 from
tree-sitter alone. So the overlay kept its guard and lost its purpose in the same change, and the
symptom was one failing case rather than a wrong answer.

# The cause

The guard was written against one storage place, and the redesign made two. The parse still records
every call. It records a call its own file decides in `edges`, and a call that leaves the file in
`refs`.

# The fix

The guard becomes "tree-sitter recorded a call at this byte", in either place. Where no stored edge
sits at the site, `_ref_caller` looks for a `refs` row there and takes the enclosing definition as
the source. A SCIP occurrence with no parse record behind it still earns nothing.

The `refs` row stays where it is, so the derived hop would answer the same call a second time as a
ranked guess. `dbread.decided_by_scip` is what stops it: one indexed read of every `scip` call site,
memoized per query, and the whole fleet holds 31,468 such edges. `T-281` asserts both halves -- the
caller appears once and carries `evidence: scip`, and the file SCIP ruled out keeps no
caller[^case].

# What would have caught it sooner

Nothing in the plan named the coupling. `T-121` did catch it, because it asserts the parse held the
target as a candidate rather than asserting only that the tier ingests something. A case that
graded the count and not the agreement would have passed.

[^rewrite]: `_rewrite_call` and `_ref_caller` in `src/graphrag/scip/ingest.py`.
[^case]: `test_an_upgraded_cross_file_call_is_answered_once` in `tests/test_scip_ingest.py`.
