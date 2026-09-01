---
type: Attested Computation
resource: tests/test_freshness.py
title: A save is searchable before the next one lands
description: "The latency the watcher hint buys, timed end to end through the running daemon. A save on a 2,461-file Go repository becomes queryable in 127 ms at p50 and 173 ms at p99, against 34.7 s before D-51."
tags: [latency, measurement, watcher, attestation]
status: stable
runtime: python
generated: { by: claude/opus-5, at: 2026-09-01T15:40:00Z }
parameters:
  - { name: corpus, type: path, required: true }
  - { name: file, type: path, required: true }
executor:
  resource: ../skills/run-pytest-measure.md
  receipt: [test_node_id, corpus_ref, commit_sha, tree_dirty, outcome, files, n_samples, misses, edit_to_queryable_ms_p50, edit_to_queryable_ms_p99, whole_tree_pass_s]
attester:
  resource: ../attesters/freshness_receipt.py
stale_after: 2027-09-01T00:00:00Z
sources:
  - id: freshness-run
    resource: tests/test_freshness.py
    last_modified: 2026-09-01T00:00:00Z
  - id: overlay-defect
    resource: ../defects/the-overlay-ran-on-every-save.md
    last_modified: 2026-09-01T00:00:00Z
---

# The claim

`D-48` made the watcher's paths a hint, so a save hashes the named files and not the tree. The
claim that stage bought is a latency, and a latency is not a property any fixture can show. So the
run drives a real editor-shaped save into a real repository, and the daemon holding the writer lock
is the only thing that indexes it.[^freshness-run]

Twelve saves on `go-monorepo`, 2,461 files, measured 2026-09-01 at commit `e6f2282`:

| Arm | Reading |
|---|---|
| Edit to queryable, p50 | 127.4 ms |
| Edit to queryable, p99 | 173.1 ms |
| Saves that never became queryable | 0 of 12 |
| Whole-tree read, the before-arm | 1.08 s |

The criterion is one second, and the p99 sits at a sixth of it.

# What the before-arm is, and what it is not

`whole_tree_pass_s` times `discover.enumerate_files` alone, and not a pass. The daemon holds the
writer lock during the run, so a second whole pass cannot execute beside it. The figure is the
read half only: enumerate the tree, stat every candidate and hash every file. That is the term the
hint removes, and it is the honest half to compare against.

Read it as an order of magnitude and not as a constant. The same call read 228-252 ms on an idle
machine, and 1.08 s here, because the daemon is indexing 375 projects underneath it.

# The reading this measurement was built to catch

The first live samples of this stage read **34,704 ms** and **60,848 ms**, with `queue_depth` 0 at
both instants. So the wait was inside the pass and never in the queue, and the exit criterion of
one second was missed by a factor of 35.

The cause was the SCIP overlay, which ran on every hinted save and re-read 1.8 M occurrences
whatever changed.[^overlay-defect] `D-51` moved it onto the unhinted reconciler pass, the way
`reclaim` already rode it. The figures above are the same measurement after that one condition.

# Why a miss is a field and not an absence

`misses` counts a save that never became queryable inside the deadline. A run that dropped the row
would report the worst reading as silence, and a p50 over eleven samples would look healthy while
the twelfth save was lost. The test asserts `misses == 0` before it writes the receipt, and the
attester grades the field.

[^freshness-run]: `tests/test_freshness.py`, T-287. Opt-in: it needs `GRAPHRAG_FRESHNESS_ROOT`, `GRAPHRAG_FRESHNESS_FILE` and a daemon answering `/healthz`.
[^overlay-defect]: `knowledge/defects/the-overlay-ran-on-every-save.md` carries the cProfile table.
