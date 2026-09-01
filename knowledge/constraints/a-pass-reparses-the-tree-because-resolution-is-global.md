---
type: Constraint
resource: src/graphrag/index.py
title: A pass reparses the tree, because resolution is global
description: "Every reference is scored against the whole symbol table. A pass that reparsed only the edited file would price every other file as a repo that does not define the name. Per-file facts are not persisted, so there is nothing to reuse."
tags: [indexing, resolution, watcher, progress]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T06:54:11Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
sources:
  - id: pass
    resource: src/graphrag/index.py
  - id: watcher
    resource: src/graphrag/watch.py
---

# What the engine actually does on an edit

The content hash decides staleness. Where any file moved, `_facts` parses every parsable file in
the tree.[^pass] Phase two then scores each reference against the whole symbol table.

# Why one file is not enough

A candidate set is built from every definition in the project. Parse one file and the other files
carry no definitions, so each name in the edited file scores as a repo that defines it nowhere and
becomes an external node. That is a wrong answer rather than a slow one.

Facts are not written to the store, only nodes and edges are. So there is no cached parse to reuse
even where the resolution question allowed it.

# What the watcher does guarantee

One index pass per project, never one per file.[^watcher] Two edits inside one debounce window
raise a single job, and a job already queued for that project is dropped rather than added.

# What would have to be true to revisit this

Persisted per-file facts, plus a resolution phase that reads the stored symbol table rather than
rebuilding it. Both are real work, and neither is bought by the throughput measured today.

# What changed on 2026-09-01, and what did not

The falsifier above named exactly this change, and half of it is now bought. `refs` and `imports`
persist every per-file fact, and resolution reads the store rather than a rebuilt symbol table. See
[a build-free engine resolves at query time](../decisions/a-build-free-engine-resolves-at-query-time.md).
So the title's stated cause is gone: the pass no longer reparses the tree *because resolution is
global*.

The pass still reparses the tree, for a second reason this record never named. `_facts` parses every
file the scan reports as moved, and `discover.enumerate_files` reads and SHA-256-hashes every file
in the tree before that -- 228-252 ms on `go-monorepo`, 2,461 files, measured 2026-09-01. That scan is the
remaining cost, and it is a separate piece of work.

# The write is per file since 2026-09-01, and the scan is not

The per-file rewrite landed. See
[an index pass rewrites only the files that changed](../decisions/an-index-pass-rewrites-only-the-files-that-changed.md).
So the title is now false about the **write**: a pass parses and rewrites the files the diff names
and no others, and `T-256` asserts that an untouched file keeps its node ids.

The title stays true about the **scan**, and that is the only claim this record still carries.
`discover.enumerate_files` reads and SHA-256-hashes every file in the tree before the diff exists --
228-252 ms on `go-monorepo`, 2,461 files. That is the floor on save-to-searchable today, and it is about
eight times the per-file parse this work bought. Removing it is `D-48`: the watcher already knows
which paths changed and throws that answer away.

The whole-tree hash is not deleted when `D-48` lands, and it must not be. The question it answers is
*does the graph match the disk*, which stays correct after a crash, after a missed inotify event and
after a week of downtime. The hint buys latency. The scan buys correctness.

[^pass]: `index._facts`, which drives the progress file over the parsable set.
[^watcher]: `watch._submit`, one `QUEUE.submit` per project the batch touched.
