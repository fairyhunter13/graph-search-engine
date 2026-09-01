---
type: Decision
resource: src/graphrag/dbread.py
title: A build-free engine resolves at query time, and stores only what one file decides
description: "No work that depends on more than one file may happen at index time. A same-file and a same-class reference is decided by its own file and stored as an edge. Every reference that leaves its file is a `refs` row, scored on read."
tags: [resolution, indexing, query, incrementality]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: dbread
    resource: src/graphrag/dbread.py
  - id: derive
    resource: src/graphrag/derive.py
  - id: split
    resource: src/graphrag/indexwrite.py
  - id: guard
    resource: tests/test_resolvedb.py
---

# The choice

The invariant is narrower than "resolve at query time", and the difference carries the design.
**No work that depends on more than one file may happen at index time.** A build-free engine still
precomputes. It precomputes only what one file answers alone.

Four systems were compared against that rule.

| System | Needs a build | Cross-file work at | A one-file edit costs |
|---|---|---|---|
| Kythe, CodeQL, every SCIP indexer | yes | index time | a rebuild |
| GitHub stack-graphs | no | query time | one file |
| rust-analyzer, rustc, Roslyn | no | index time, memoized | the file plus its dependents |
| graphrag before this commit | no | index time, unmemoized | the whole tree |

graphrag was the only row that paid whole-tree cost for a one-file edit, and every symptom followed
from that one place.

# The split, and why it is sound

A reference its own file already decides is file-local too. So it resolves at index time and becomes
a stored edge: `same_class` at 0.95 and `same_file` at 0.90[^split]. Every other reference becomes a
bare `refs` row and is scored on read[^derive]. A reference is written to exactly one of the two
places, so no answer counts it twice.

The soundness argument, written down because it is not obvious:

1. `SAME_CLASS` and `SAME_FILE` are the top two tiers, and `_rank` keeps only the best tier. No
   candidate outside the file can beat a same-file candidate, so the whole-tree pool cannot change
   that answer.
2. One rule can drop a same-file candidate before it is tiered, and that is `_receiver_modules`. It
   reads that file's imports and that file's own module name, so it is file-local too.
3. An empty pool means external, and only the whole tree proves a pool empty. Index time never
   asserts that. It asserts a positive -- a candidate exists here -- so it never needs the tree.

# What a query costs

Five inputs decide a reference. Four are file-local or pure, and one is global: the candidate pool,
read from `nodes` on the existing `nodes_name` index[^dbread]. So one reference costs two indexed
seeks plus one small per-file read, and `Context` memoizes that read for every reference in the file.

Measured over all 375 stores, 898 MB, on 2026-09-01: a median name resolves in 17-75 µs, `Equal` in
the Go monorepo at 8,704 rows in 1 ms, and the fleet worst, `n` in the web tree at 90,643 rows, in
10 ms. `nodes.name` is near-unique in the body of the distribution -- median 1 node per name, p90 at
most 3, in every store.

# Why the memoized alternative was rejected

Row 3 of the table is what rust-analyzer, rustc and Roslyn do, and the stack-graphs paper rejects it
only because GitHub must serve every historical commit of millions of repositories. That reason does
not apply here: this engine holds one live version of every file. So the option was open, and it was
tested against the fleet rather than argued.

A reverse-dependency map is the `IMPORTS` edge in this engine. Census over the whole store
directory, 2026-09-01: 2,474 `IMPORTS` edges, held by **7 of 375 stores**. The invalidation input
exists in under 2% of the fleet, and building it is per-language module identity over 68 grammars,
which must be correct in *every* language before the invalidation is safe. A wrong dependency edge
does not make the engine slow. It serves a stale answer, silently, and no test sees it.

Query-time resolution needs no such map. It reads the raw import string on every query, so it stays
correct while module identity is still wrong, and it improves the day module identity lands with no
reindex.

# Why the stack-graphs machinery is declined

Its incrementality comes from symbol stacks, partial paths and a per-language binding DSL over
`tree-sitter-graph`. Those rules are written per language, and this engine covers 68 tagged grammars.
The DSL cost there is Java 1,366 lines, Python 1,377, JavaScript 5,058 and TypeScript 6,297, with no
Go and no PHP after several years of GitHub funding. All of graphrag is about 6,400 lines. GitHub
archived the repository on 2025-09-09.

What is taken is the principle and one table shape. stack-graphs stores, per file, what the file
needs from outside as an indexable string, then joins across files with one indexed prefix query.
`refs` and `imports` are this engine's version, keyed on `name` and on `module` rather than on a
symbol stack. That is the deliberate simplification, and it is what makes it a week and not a
quarter.

# The kill criterion that would reverse this

The two-engine caller computation stops scoring F1 1.000, or a hot name costs more than the 10 ms
the fleet census measured. Either one means the derivation changed an answer or priced one wrong,
and the split is then re-argued rather than tuned.

# What this decision does not cover

The scan in front of the pass. `enumerate_files` still hashes every file, at 228-252 ms on the Go monorepo,
and no part of this record removes it. The reparse and the scan are two separate costs, and
[the reparse constraint](../constraints/a-pass-reparses-the-tree-because-resolution-is-global.md)
records which half this commit bought.

[^split]: `resolve.resolve_file_local` and `indexwrite.reference_edges`, the index-time half.
[^derive]: `derive.hop` and `derive.radius`, which ask the stored and the derived source at each level and merge them.
[^dbread]: `dbread.Context`, one connection plus the memos that keep a hot name affordable.
[^guard]: `test_the_two_resolvers_agree_over_this_repo` runs both resolvers over this repo's own source and compares every candidate set.
