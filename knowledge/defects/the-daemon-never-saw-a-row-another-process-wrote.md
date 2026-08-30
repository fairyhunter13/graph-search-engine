---
type: Defect
resource: src/graphrag/watch.py, src/graphrag/tools.py, tests/test_watch.py
title: The daemon never saw a row another process wrote
description: "`rearm_if_changed` had one caller, inside the watch loop and only after a prune. `graphrag index` enrols from the operator's own process, so a row added that way was watched only after a restart. Its changes were never indexed and its deletion was never seen."
tags: [watcher, registry, federation, pruning, inotify]
status: stable
generated: { by: claude/opus-5, at: 2026-08-30T00:00:00Z }
---

# What was observed

Two throwaway projects were enrolled with `graphrag index` against a running daemon. The daemon had
logged `watching 367 projects` at startup, and it went on logging that number. Both new rows were in
`projects.json`, and neither was in the watch set.

One of the two directories was then deleted. Nothing happened. The row for a project the filesystem
no longer held survived every grace period, because no event ever reached the process that measures
one.

# Why it happened

`rearm_if_changed` existed, and it was correct. It had exactly one caller: the watch loop, on the
branch that runs after a prune actually removed something. Nothing called it on enrolment.

The reference engine calls the same function from four places, two of them enrolment paths. The port
took the function and left its callers behind, which is a shape a reading of `watch.py` alone cannot
show: the module is complete and the hole is in every other module.

`graphrag index` makes the gap wider than a missing call would suggest. It runs the pass in the
operator's own process rather than asking the daemon, so the daemon is not merely late to hear about
the new row. It is never told at all.

# The two consequences, and the second is the quiet one

A project whose changes are never indexed answers stale, and a person notices that.

A project whose **deletion** is never seen answers nothing, and nobody notices. Automatic removal is
armed on a delete event, and an unwatched path produces no events. So the rule in
[a row leaves on a delete event](../decisions/a-row-leaves-on-a-delete-event-and-never-on-a-scan.md)
was live and unreachable for every row the daemon did not personally write.

# The fix

`enroll` re-arms, which covers the MCP tool and the daemon's `/register` route. The watch loop also
re-arms on every tick, which covers the CLI and anything else that writes the registry from outside.

The tick runs once a second, so `rearm_if_changed` stats the registry file before it parses it, and
returns on an unchanged mtime and size. `_roots()` parses every row, and the guard is what makes a
per-second call affordable.

`doctor --prune` still owns what neither reaches: a project deleted while the daemon was down.
inotify has no replay, and a row for a path that is already gone is filtered out of the watch set by
`_roots()`, so it can never produce the event that would remove it.
