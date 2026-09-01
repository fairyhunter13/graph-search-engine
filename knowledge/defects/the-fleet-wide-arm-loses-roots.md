---
type: Defect
resource: src/graphrag/watch.py
title: The fleet-wide arm loses roots
description: "Two enrolled projects have zero rows in the whole watch-ledger history, while each has 8 index rows. Every predicate passes for both. Armed alone on two roots, `watchfiles` delivers an event for each in 12 s. So the library and the trees are sound, and the fault is in arming 375 roots in one call."
tags: [watcher, inotify, daemon]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: loop
    resource: src/graphrag/watch.py
---

# What is wrong

`watch._loop` arms every enrolled root in one `watchfiles.watch` call[^loop]. On 2026-09-01 that
was 375 roots. Two of them never deliver an event:

| Project | Watch-ledger rows | Index rows | Directories |
|---|---|---|---|
| `gen2-php-app` | 0 | 8 | 1,548 |
| `web-tree` | 0 | 8 | 4,128 |

Zero across `watch.jsonl` and `watch.jsonl.1` together, which is the whole history the ledger holds.
A change in either project reaches the graph only through the unhinted reconciler pass.

# What was ruled out

Every predicate the watcher applies passes for both roots:

1. Both are in `watch._roots()`, which returned 375.
2. `filters.language_of` returns `php` for one and `javascript` for the other.
3. No part of either path is a skipped directory.
4. `watch._owner` returns the right project for a file inside each.
5. Neither path is a symlink.

A probe wrote a file at the root of each tree and deep inside each tree, then read the ledger. One
row came back, and it named only `largest-enrolled-project` and `go-monorepo`.

# What isolated it

`watchfiles.watch` was armed on those two roots **alone**, in a separate process, and a probe file
was written and removed in each. Both events arrived, in 12 s:

```
/home/<user>/git/github.com/Acme/gen2-php-app/zzprobe_wf.txt
/home/<user>/git/github.com/Acme/web-tree/zzprobe_wf.txt
```

So the library delivers, the trees are watchable, and the inotify limits are not reached. The fault
is in the fleet-wide arm.

# Why it is recorded and not fixed

It is pre-existing. The ledger shows zero rows for both roots across its entire history, including
every entry written before the watcher gained its path hint, so it is not a regression of that work.
The engine stays correct without it, because the unhinted reconciler is what heals a change no event
reported, and `T-274` asserts exactly that. What is lost is latency on two projects, not an answer.

The next step is to bisect the arm: halve the root list until the two roots reappear, and read
whether the loss is a count, a total directory count, or an ordering.
