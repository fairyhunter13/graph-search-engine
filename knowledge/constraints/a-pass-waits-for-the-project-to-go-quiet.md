---
type: Constraint
resource: src/graphrag/index.py, src/graphrag/watch.py, src/graphrag/config.py
title: A pass waits 15 seconds for the project to go quiet, and a query may be that far behind the disk
description: "Deprecated on 2026-09-01 with `WATCH_QUIET_MS`. The window hedged a whole-tree pass, and `D-47` made the pass per file, so the 15 seconds became pure latency. Watch batches carried one event each, 5 to 20 seconds apart, so the debounce merged almost nothing and every save bought a whole-tree pass. The countdown restarts on each event, and an explicit index call pulls the job forward."
tags: [watcher, indexing, throughput, freshness, deviation]
status: deprecated
generated: { by: claude/opus-5, at: 2026-08-27T00:00:00Z }
sources:
  - id: queue
    resource: src/graphrag/index.py
  - id: run-ledger
    resource: ~/.local/share/graphrag/ledgers/run.jsonl
---

# What the ledger showed

89 passes an hour for `graph-search-engine` and 55 for the largest enrolled project, from batches carrying one
event each.[^run-ledger] They arrived 5 to 20 seconds apart, median 11. `WATCH_DEBOUNCE_MS` is the
Rust batch window inside `watchfiles` and merges nothing at that spacing: at 400 ms, 95 to 98
percent of those passes survive it. Raising it to 1500 ms would still have merged almost nothing.

# What the window is

An event queues the project and starts a `WATCH_QUIET_MS` countdown. A further event on the same
project restarts it, so a pass runs once the person stops typing rather than once per save. Against
the same ledger, 89 and 55 passes an hour become 37 and 35.

# The cost, stated

A query may be `WATCH_QUIET_MS` behind the disk, on top of the pass itself. That is the whole of
what the window trades. An explicit `index` call submits with no delay, and it also pulls a waiting
job forward, so a caller that wants the tree now is never held by someone else's countdown.

# What the queue had to grow

`take` skips a job whose countdown is still running, so polling `take` until it returns `None` no
longer empties the queue. `Queue.drain` discards what is waiting, countdown included.[^queue]

[^run-ledger]: The daemon's own run ledger, read over one hour on 2026-08-27.
[^queue]: `index.Queue.drain`, used by the watcher tests between cases.

# Deprecated on 2026-09-01, and what replaced it

`WATCH_QUIET_MS` is deleted. See
[the watcher hints which files changed and the scan reconciles](../decisions/the-watcher-hints-and-the-scan-reconciles.md).

The window bought one whole-tree pass per burst of saves, and it cost every query up to 15 seconds
of staleness on top of the pass. `D-47` made the pass rewrite the files the diff names, and `D-48`
made the watcher hand those names over, so a save costs a hinted diff and a per-file write. At that
price the hedge is worth less than the latency it charges.

The measurement above stands as written. 89 passes an hour is unaffordable at whole-tree cost and
cheap at per-file cost, so the same figure argues the opposite way once the cost moves.

`Queue._ready`, the countdown in `_pop_ready` and the `delay` argument all go with the window.
`Queue.drain` stays, and its reason narrows: it discards what is waiting, and there is no countdown
left for a `take` to skip.
