---
type: Defect
resource: src/graphrag/index.py
title: The overlay ran on every save
description: "A hinted pass on `go-monorepo` took 29.6 s of work for one changed file, and the SCIP overlay was 49 s of a 58 s profiled pass. The overlay re-runs the indexer and re-reads 1.8 M occurrences whatever changed, so it has no per-file form. It now rides the unhinted reconciler, the way `reclaim` does."
tags: [scip, latency, indexing, watcher]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: overlay
    resource: src/graphrag/index.py
  - id: ingest
    resource: src/graphrag/scip/ingest.py
---

# What is wrong

The watcher hint made a pass parse one file instead of the tree. On the bench that pass measured
15-18 ms. Live, through the daemon, a save on `go-monorepo` was queryable after 34.7 s, and the second
sample read 60.8 s. The exit criterion for the stage is one second.

The gap is not the queue. The run ledger shows the watch event at ts 1788249859.4 and the hinted
index row at 1788249894.1, and the queue was empty at both instants.

# The measurement that found it

The daemon was stopped, and one hinted pass ran under `cProfile` against the live `go-monorepo` store,
2026-09-01. It parsed 1 file and it took 57.8 s:

| Cost | Reading |
|---|---|
| `scip.ingest.ingest`, cumulative | 49.1 s over 8 calls |
| `scip.read._document`, cumulative | 34.4 s over 4,166 documents |
| `scip.read._occurrence` | 1,806,986 calls |
| `select.poll`, the indexer subprocess | 9.8 s |
| Everything else the pass names | under 15 ms total |

So a one-file save re-ran the SCIP indexer as a subprocess, then re-read the whole artifact.

`go-monorepo` carries no `.graphrag.yaml` of its own. It inherits `scip` and `scip_indexers` from a
claiming root, which is why the tier was live on a repository whose own tree does not ask for it.

# What holds it

The overlay has no per-file write. `ingest` reads a whole SCIP artifact, and the artifact is stale
the moment any file changes. So the overlay is the same shape as `reclaim`: whole-tree work that
belongs on the whole-tree pass. `index_once` now runs it only when the pass is unhinted, and
`T-286` asserts both directions.

# What the fix costs

A hinted save carries no `scip` tier for the file it rewrites, until the next unhinted pass. That is
the hint's own bargain stated once more: the hint buys latency and the scan buys correctness. A
`scip` edge is an upgrade over a syntactic one, never the only edge, so the file stays answerable at
the lower tier in the meantime.

See [reclaim never reclaimed a page](reclaim-never-reclaimed-a-page.md) for the precedent, and
[the overlay writes an FTS column and never the index](the-overlay-writes-an-fts-column-and-never-the-index.md) for the coupling that stays latent.
