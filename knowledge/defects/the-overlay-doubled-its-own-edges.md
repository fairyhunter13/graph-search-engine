---
type: Defect
resource: src/graphrag/scip/ingest.py
title: The overlay doubled its own implements edges on the second run
description: "A call edge is keyed by its call site byte and replaces itself. An implements edge was keyed by nothing, so a second ingest of one index inserted every one of them again and the graph reported one interface twice."
tags: [scip, idempotence, edges]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T13:10:00Z }
sources:
  - id: ingest
    resource: src/graphrag/scip/ingest.py
  - id: case
    resource: tests/test_scip_ingest.py
---

# What happened

`ingest` writes two edge kinds. A call edge goes through `_rewrite_call`, which deletes whatever
sits at that call site byte before it inserts. An implements edge went straight to an `INSERT` with
no delete and no unique constraint behind it.

So one ingest of one index was correct and two were not. The second run inserted every implements
edge a second time, at confidence 1.0 and `resolved = 1`. A caller asking what implements an
interface read one subtype twice and had no way to tell.

# Why nothing caught it

Every case ingested once. The overlay is re-run on every re-index of an enrolled project, so once
was the state no real deployment is ever in.

# What holds it now

`ingest` deletes this producer's own implements edges before it writes them again, and `T-125`
runs the same ingest twice and counts the rows. The delete keys on the `producer` column, which
until now was written by three modules and read by none.[^ingest]

# The general shape

An insert with no key is not idempotent, and a pass that runs on every re-index has to be. The call
edge had a key by accident, because the call site byte is what `_rewrite_call` needed anyway. The
implements edge had no such byte, so nothing forced the question.

[^ingest]: `src/graphrag/scip/ingest.py`, the delete before the implements loop.
[^case]: `tests/test_scip_ingest.py::test_a_second_ingest_replaces_its_own_implements_edges`.
