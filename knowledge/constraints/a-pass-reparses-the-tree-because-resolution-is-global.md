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

[^pass]: `index._facts`, which drives the progress file over the parsable set.
[^watcher]: `watch._submit`, one `QUEUE.submit` per project the batch touched.
