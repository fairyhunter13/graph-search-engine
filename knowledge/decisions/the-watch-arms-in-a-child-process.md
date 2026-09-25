---
type: Decision
resource: src/graphrag/watch.py, src/graphrag/watchchild.py, tests/test_watch.py
title: The watch arms in a child process, because arming holds the GIL
description: "watchfiles' `RustNotify` holds the GIL while its inotify thread walks every watched directory. In the daemon that stops every thread, the watchdog pinger among them. coderag lost 7 restarts to it on 2026-09-25, and this engine runs the same call over 103,476 watches."
tags: [watcher, availability, watchdog, gil]
status: stable
generated: { by: claude/opus-5, at: 2026-09-25T20:15:00+07:00 }
---

# Decision

`watch._watch` is `watchchild.arm`. It runs `watchfiles.watch` in `python -m graphrag.watchchild`
and reads one JSON line per batch from a pipe. The arming walk holds the child's GIL, so the
daemon's event loop, worker and pinger keep running.

# Why

coderag's core dump of 2026-09-25 showed the mechanism. One thread held the GIL in
`RustNotify.__new__`, waiting for `notify`'s event-loop thread to finish `add_watch` over every
directory. Every Python thread waited, no watchdog ping went out, and systemd killed the daemon 7
times under load 27-40. This engine arms the same way, over 103,476 watches, and its journal holds 2
watchdog kills in 30 days, on 2026-09-16 and 2026-09-25. No core survives for those two, so their
cause is not confirmed. watchfiles 1.3.0 does not release the GIL there.

Over 60,000 directories, a 10 ms heartbeat stalls 0.55-0.62 s during an in-process arm and 0.01 s
during a child arm. `T-360` holds the second number under 0.25 s.

# What moved with it

`watch_filter` is `_keep`, a closure over this process's `_keys` and `_links`. It cannot cross a
process boundary, so `arm` applies it to each batch as it arrives. A batch the filter empties is
the same empty tick `yield_on_timeout` already produced.

`armed()` is new. The child only writes its first batch once its watches are in place, so "the
loop chose these roots" and "these roots are watched" are now a Python start and a walk apart. The
two watch tests that wrote a file as soon as `_intent` moved now wait for `armed()`.
