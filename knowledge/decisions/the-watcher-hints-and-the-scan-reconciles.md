---
type: Decision
resource: src/graphrag/watch.py, src/graphrag/jobs.py, src/graphrag/index.py
title: The watcher hints which files changed, and the whole-tree scan reconciles
description: "inotify already answers what changed, and `_submit` threw the answer away and submitted a bare root string. The paths ride along as a hint now, so a save hashes those files and not the tree. The hint never replaces the scan: inotify has no replay, so only the unhinted pass heals an event no process saw."
tags: [watcher, indexing, incrementality, latency, freshness]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: watcher
    resource: src/graphrag/watch.py
  - id: queue
    resource: src/graphrag/jobs.py
  - id: pass
    resource: src/graphrag/index.py
  - id: guard
    resource: tests/test_watch.py
---

# The choice

`D-47` made the write per file and left the scan whole. So the floor on save-to-searchable stayed
`discover.enumerate_files`, which stats every candidate and then reads and SHA-256-hashes it: 228 to
252 ms on the Go monorepo, 2,461 files. That is about eight times the per-file parse `D-47` bought.

The watcher already held the answer that scan rediscovers. `_submit` counted the events per owning
project and submitted the root string alone[^watcher]. The paths are the hint now, and
`index_once(root, paths=...)` stats and hashes those files only[^pass].

# What the hint is not

It is not the source of truth, and it must never become one. inotify has no replay. An event lost
to a re-arm, to a crash or to a week of downtime is lost for good, and a watcher-only engine goes
quietly stale with no test to see it. So the unhinted pass stays exactly as it was, and it is what
the daemon runs on start for every enabled row.

The hint buys latency. The scan buys correctness. `T-274` asserts that an unhinted pass finds a
change no event reported.

# Three rules that make a hint safe

**The stored rows are narrowed to the hint.** A hinted pass diffs the named paths against their own
`files` rows. Diffed against every stored row, each file the hint does not name would read as
removed, and the pass would delete the project one save at a time.

**The dedup becomes a merge.** Dropping a second submission for a queued root was correct while a
job meant *reindex everything*. It loses paths the moment a job names them, and those files stay
stale until the next unhinted pass. A hinted job merged with an unhinted one becomes unhinted,
because a scan covers any hint[^queue].

**A hint has a cap, and the merge is capped too.** `WATCH_HINT_MAX_PATHS` is 200. A branch switch
moves thousands of files inside one 400 ms debounce window, and rewriting them one at a time costs
more than one scan. Past the cap the hint is dropped and the job falls back to the scan. Two hints
under the cap can sum past it, so the merge applies the same rule.

# What a hinted pass must not record

`report.languages` is computed from the files the pass read, and `index.record` turns it into the
registry's capabilities. A hinted pass saw one save's worth of files, so writing those would narrow
the project to the language of whatever was last edited. `IndexReport.hinted` is what holds the
capability write back, and `force` and a rebuild both drop a hint for the same reason: neither has
rows for a hint to diff against.

# What stays, four lines from what went

`WATCH_DEBOUNCE_MS` is the `watchfiles` batch window and is a different thing. `WATCH_POLL_MS` with
`yield_on_timeout=True` is what makes the loop yield an empty batch every second, and that empty
batch is the only clock `prune.run_due` and `rearm_if_changed` are measured against. Deleting it
would stop pruning and stop the watcher ever seeing a project another process enrolled, and no prune
test would fail. `T-275` holds it.

[^watcher]: `watch._submit`, one `QUEUE.submit` per project the batch touched, with the paths.
[^queue]: `jobs.Queue.submit`, which returns `queued`, `merged` or `requeued`.
[^pass]: `index.index_once`, and `discover.enumerate_paths` under it.
