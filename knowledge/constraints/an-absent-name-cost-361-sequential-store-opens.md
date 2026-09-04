---
type: Constraint
resource: src/graphrag/tools.py, src/graphrag/fanout.py
title: An absent name cost 361 sequential store opens, and a window is what fixes it without losing the early stop
description: "`find_symbol` walked the root plus every member one store at a time. Over the 361-project unit on this host an absent name took a median 57.45 s; four workers in windows took 24.91 s, 2.31x. A plain map over the whole list would have been the wrong fix: a common name is answered by the first store, so a full map would open 361 stores to save nothing."
tags: [federation, latency, threads, memory]
status: stable
generated: { by: claude/opus-5, at: 2026-09-04T00:00:00Z }
sources:
  - id: fanout-module
    resource: src/graphrag/fanout.py
  - id: find-symbol
    resource: src/graphrag/tools.py
  - id: fanout-tests
    resource: tests/test_fanout.py
---

# The shape of the walk

`find_symbol` is the one federated tool here. `federation.expand` returns the root first and then
its members, and the loop opened one store, read it, closed it and moved to the next. It stopped
as soon as it held `limit` hits.

That stop is why the loop looked cheap. A common name is answered by the first store, so the
common case opens one. The cost sits entirely on the other case: **a name that is absent, or rare,
opens every store in the unit**.

The largest unit on this host is **361 projects**. That is the same unit the sibling engine hit
this defect on, and its own bundle records the fix under `what a root and 135 members cost`. 380
graphs sit on disk here against 377 registry rows.

# The measurement

One absent name, `zzz_no_such_symbol_anywhere`, over that 361-project root. Three passes per arm,
alternated one against the other so machine drift lands on both:

| workers | pass 1 | pass 2 | pass 3 | median |
|---|---|---|---|---|
| 1 (the old loop) | 150.15 s | 45.72 s | 57.45 s | **57.45 s** |
| 4 (windowed) | 24.91 s | 16.73 s | 29.54 s | **24.91 s** |

**2.31x, and the figure is directional and not a p95.** The 1-minute load average was **19.10**
while it ran, and the 150.15 s first pass is a cold page cache rather than an arm. What the run
does establish is the shape: both arms answered `searched=361, hits=0`, so the two walks read the
same stores and returned the same answer.

# Why a window, and not one map over the list

The obvious fix is `Executor.map` over the whole member list. It is the wrong one here, and the
reason is the early stop.

`map` submits every item at once. So a full map opens all 361 stores whatever the answer is, and
the common name that used to cost one store would start costing 361. It would make the cheap case
361x worse to make the rare case 2.31x better.

`fanout.windowed` is a generator that submits `FANOUT_WORKERS` items, yields those results in the
order asked, and only then submits the next window. A caller that stops reading stops the walk.
The waste is bounded at `FANOUT_WORKERS - 1` stores, which is 3.

Two properties are asserted rather than assumed, and each has an arm that fails the version that
gets it wrong:

- **In the order asked, never as the threads finish.** The root is first and the caller keeps the
  first `limit` hits, so an order set by disk timing would change which project answers.
  `T-338` sleeps longest on item 0 and asserts both that the answer is in order *and* that the
  work finished out of order — without the second assertion a plain sequential loop passes it.
- **One window per stop.** `T-339` consumes one result from a 40-item walk and asserts at most 4
  items were opened. Against a full map it reads 40.

# The one behaviour that had to change

The sequential loop passed a shrinking limit: `limit - len(results)`. A worker cannot have that
number, because the projects before it may not have finished. So every worker asks for the whole
`limit` and the caller truncates. A store therefore reads up to `limit` rows where it used to read
fewer, and `limit` defaults to 20.

`_connect` raises `LookupError` for a member with no graph. The loop caught it per project and
carried on. Across a pool that exception surfaces at the consuming loop instead, and every member
after the unindexed one would go unread — so the worker catches it and returns `None` for the hit
list. `T-341` is that case on a real two-project federation.

# What this does not claim

It does not move graphrag's resident memory, which is 227 MB after seven days and near the floor
for a Python daemon holding 371 grammars. Four workers is a bound on descriptors and disk, not on
CPU, and it is the same count and the same reasoning coderag settled on.

`GRAPHRAG_FANOUT_WORKERS=1` restores the sequential loop exactly — not a pool of one, because a
pool of one still moves the work to another thread. `T-340` asserts the work ran on the calling
thread.
