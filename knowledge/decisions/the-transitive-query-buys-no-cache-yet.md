---
type: Decision
resource: src/graphrag/query.py
title: The transitive query buys no cache yet, and the measurement says where one would go
description: "`blast_radius` at depth 3 was measured on two corpora before and after the stage-1 redesign and after `D-40`. On a 167-file repo p99 is 16.7 ms and no cache is warranted. On a 2,461-file Go monorepo p99 is 12.9 s and 37% of calls exceed a second — but cost per reached node fell 8.9 times over the same change, so the query got dearer by answering more, and a cache keyed on the start node and the depth is what the figure argues for."
tags: [query, transitive, measurement, cache, go]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: blast
    resource: src/graphrag/query.py
  - id: memo
    resource: ../decisions/a-build-free-engine-resolves-at-query-time.md
---

# The ruling

No memo cache is written. The plan made the cache conditional on the measurement, the measurement
was taken, and on the corpus this engine is developed against it says no. On the larger corpus it
says a cache would pay — but not the one the plan had drafted, and the reason is in the numbers.

# What was measured

`query.blast_radius`[^blast] at `depth=3`, sampled node ids, three builds of the engine over the
same two stores. Corpus A is this repository: 167 files, 851 non-module nodes, 300 sampled ids.
Corpus B is a 2,461-file Go monorepo: 24,448 non-module nodes, 193 ids paired across all three
builds so every arm answers the same questions.

| corpus | build | p50 | p99 | mean reach | ms per reached node |
|---|---|---|---|---|---|
| A | pre-stage-1 | 1.66 ms | 12.63 ms | 13.77 | — |
| A | current | 3.39 ms | 16.68 ms | 15.36 | — |
| B | pre-stage-1 | 32.7 ms | 4,586 ms | 9.39 | 29.14 |
| B | stage-1, pre-`D-40` | 33.0 ms | 4,562 ms | 9.39 | 30.09 |
| B | current | 81.3 ms | 12,935 ms | 80.27 | 3.37 |

Three readings, and the third is the one that decides.

**The stage-1 redesign moved nothing.** On corpus B the pre-stage-1 and post-stage-1 arms are the
same measurement: 32.7 against 33.0 ms at p50, 4,586 against 4,562 at p99, reach identical to two
decimals. Whatever the transitive query costs, stage 1 is not why.

**`D-40` is the whole difference, and it is a reach change.** Mean reach 9.39 to 80.27 — 8.5 times.
That is Go member calls that resolved `external` before now resolving to the package they name, so
the query traverses edges that were previously dead ends. p99 rose 2.8 times against a reach that
rose 8.5 times.

**Cost per reached node fell 8.9 times**, 30.09 ms to 3.37. The query did not get slower. It got
larger, and the per-unit cost of being larger fell, because the fixed per-call work is now amortised
over a real answer instead of a truncated one. A latency figure read without the reach beside it
would have read this as a regression and reverted the fix.

# Where a cache would go, and why not the drafted one

The drafted cache was a table of resolved one-hop edges invalidated by name. It is the wrong
instrument for what was measured. 37% of corpus-B calls exceed a second (72 of 193, against 61
before), and the cost tracks the size of the reached set, not the price of any one hop. Caching hops
spreads the saving across every call including the 63% that are already fast.

What the figure argues for is a memo on the whole answer, keyed on the start node and the depth,
for the high-fan-out hubs — max reach on corpus B is 431 nodes against 100 before `D-40`. That
inherits the invalidation problem this repo already ruled on[^memo]: the fleet's `IMPORTS` edge, the
input a name-keyed invalidation would need, exists in 7 of 375 stores.

So it is not written here. It is written when a caller on a corpus-B-sized store asks for depth 3
often enough to notice, and the invalidation input exists to make it correct.

# What would have to be true to revisit this

Corpus A's p99 crosses 100 ms, or a caller reports the corpus-B p99 as a real cost rather than a
benchmark number. Either reopens this, and the table above is the baseline the next run compares
against.

# Why this is a Decision and not an Attested Computation

Its corpus is a private repository. A reader cannot fetch it, so no receipt they could re-run would
attest anything, and a `stale_after` on a figure nobody else can reproduce is a date with no owner.
The numbers are recorded for what they decided, not as a contract.

[^blast]: `query.blast_radius`, bounded by `depth`, four edge kinds.
[^memo]: The same invalidation input the build-free ruling measured and rejected.
