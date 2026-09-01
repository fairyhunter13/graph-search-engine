---
type: Decision
resource: src/graphrag/index.py
title: An index pass rewrites only the files that changed
description: "The pass narrows what it rewrites and keeps one transaction. The whole-tree `DELETE FROM files` is gone, and the cascade from one file row now takes exactly the rows that pass is about to write back."
tags: [indexing, incrementality, fts, transactions]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: pass
    resource: src/graphrag/index.py
  - id: rewrite
    resource: src/graphrag/indexwrite.py
  - id: guard
    resource: tests/test_perfile.py
---

# The choice

A pass deleted every file row and wrote the whole tree back. So a one-character edit in one file
priced as a rebuild of the project, and every symptom in this engine followed from that: the 15 s
quiet window, the queue that serialized long writes, and a query up to one whole pass behind disk.

The pass now takes the set `discover.diff` already computes and rewrites those files only[^pass].
`force` still asks for the whole tree by name, and so does a rebuild through `store.incompatible`.

# Why the cascade is exact, and why it was not before

Deleting one `files` row cascades to that file's `nodes`, and `nodes` cascades to `edges` on **both**
`src` and `dst`. So a stored edge that pointed *into* the rewritten file died with it, and the pass
never rebuilt it, because rebuilding it needs the other file. That is what made a per-file delete
unsafe.

[A build-free engine resolves at query time](a-build-free-engine-resolves-at-query-time.md) removed
every stored cross-file reference edge first. Both ends of every stored reference edge now live in
one file. So this decision depends on that one and could not have shipped before it.

# What the whole-tree delete was doing silently

`nodes_fts` is external-content and takes no cascade, and `SCHEMA` carries no trigger. The old pass
hid that behind `rebuild_fts`, which rebuilds every posting from `nodes` -- the exact cost a
per-file rewrite exists to remove. `forget_files` replaces it: it reads `name`, `qualified_name` and
`signature` of the file's nodes **before** the delete, issues one `'delete'` per row with those old
values, and only then drops the file[^rewrite]. An external-content `'delete'` given the *new*
values leaves the old postings standing, and the symptom is `find_symbol` answering a renamed symbol
under its former name at a location that no longer exists. `T-278` is that case[^guard].

`rebuild_fts` stays callable, and the SCIP overlay is its only caller. See
[the overlay writes an FTS column and never the index](../defects/the-overlay-writes-an-fts-column-and-never-the-index.md).

# One transaction per pass, and never one per file

The narrowing is over *what* is rewritten, never over *when* it commits. `store.stamp` is the single
witness that the graph matches the algorithm, and there is no such point if each file commits alone.
A reader under WAL sees the before or the after.

# What moved with it

`store.reclaim` left the per-file path. `PRAGMA wal_checkpoint(TRUNCATE)` is fsync-bound, and after
this change a pass runs on every save. The pages worth reclaiming are the ones a whole-tree rewrite
freed, so that is the only pass that calls it. `T-276` asserts both directions.

# The kill criterion

A per-file pass answers a question the whole-tree pass answered differently. The two-engine
computation is the gate, and a moved digit reverses this rather than relaxing it.

# What this decision does not cover

The scan in front of the pass. `discover.enumerate_files` still reads and hashes every file in the
tree, 228-252 ms on the Go monorepo, and no narrowing of the write touches it. See
[a pass reparses the tree](../constraints/a-pass-reparses-the-tree-because-resolution-is-global.md)
for what remains.

[^pass]: `index.index_once`, which passes `stale` to `forget_files` and `targets` to the writers.
[^rewrite]: `indexwrite.forget_files` and `indexwrite.write_fts`, the two halves of the contract.
[^guard]: `tests/test_perfile.py`, T-256 through T-280.
