---
type: Defect
resource: src/graphrag/watch.py
title: The isolation probe and the daemon did not run the same experiment
description: "Retracted 2026-09-01. Two projects were reported as receiving no watch event when 375 roots are armed in one call. All 375 roots hold an inotify watch, the descent covers every directory, and 362 of 375 projects have zero ledger rows because nobody edits them. The isolation probe wrote a file the daemon's filter refuses and the bare library run had no filter, so the two experiments were not the same experiment."
tags: [watcher, inotify, daemon, retracted]
status: deprecated
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: loop
    resource: src/graphrag/watch.py
  - id: keep
    resource: src/graphrag/watch.py
---

# What was claimed, and retracted

`watch._loop` arms every enrolled root in one `watchfiles.watch` call[^loop]. On 2026-09-01 that
was 375 roots. Two of them held zero rows across `watch.jsonl` and `watch.jsonl.1`, against 8
index rows each. Armed alone in a separate process, `watchfiles` delivered an event for each in
12 s. The conclusion drawn was that the fault is in arming 375 roots in one call, and the next
step named was to bisect the root list.

**The conclusion is wrong. Do not bisect.**

# What the retraction measured

Four readings against the live daemon, pid 857813, 2026-09-01.

**Every root is armed.** The daemon holds one inotify instance, `/proc/857813/fd/8`, carrying
68,311 watch descriptors. Each entry in `/proc/857813/fdinfo/8` names the watched inode in its
`ino:` field. Intersecting those against the directory inode of each of the 375 enrolled roots:

```
watch entries with ino: 68311
roots armed: 375   roots NOT armed: 0
```

Both of the two reported roots are in the armed set.

**The recursive descent is complete.** `os.walk` over all 375 enabled roots counts 60,475
directories, against 68,311 live watches. There is no truncation to find.

**No kernel ceiling is near.** `max_user_watches` is 1,048,576 against 217,427 held user-wide.
`max_user_instances` is 512 against the one instance a single `watchfiles.watch` call opens.

**The zero was a population of two, read against a census nobody took.** Across `watch.jsonl`
and `watch.jsonl.1` — 20,929 rows, the ledger's whole history — exactly **13 distinct projects
are ever named**. 362 of 375 have zero rows. The 13 are the projects being worked on, and their
row counts fall off a cliff: 18,162 for the first, 1,013 for the second, 820 for this repo, then
410, 234, 140, 70 and six more in double or single digits. Two quiet repositories among 362
quiet repositories is not a defect.

# Why the isolation experiment agreed with the wrong answer

The probe wrote `zzprobe_wf.txt` into each tree. The daemon's watch filter is `watch._keep`[^keep],
which admits a path only where `filters.language_of(path) != ""`:

```
zzprobe_wf.txt  ''     indexable=False
a.php           'php'  indexable=True
```

So `_keep` refuses that file, correctly, in every project. The isolation run armed
`watchfiles.watch` with **no `watch_filter`**, and the same file was delivered. The library
delivering what the daemon's filter is built to refuse is the designed behaviour. The two runs
differed in the filter, not in the number of roots.

# What holds it

The engine was never wrong here, so nothing is fixed. What was missing is a sentinel: no test
asserted that arming N roots watches N roots, which is why an arm defect would have looked
exactly like this one. `T-290` is that test, and it uses an indexable file.

The doctrine line this record broke is the one worth keeping it for: a zero is not an absence,
and a census states the population it read. This one read two.

[^loop]: `src/graphrag/watch.py` — `_loop`, the single `_watch(*_intent, ...)` arm.
[^keep]: `src/graphrag/watch.py` — `_keep`, the watcher's filter, which is the indexer's predicate.
