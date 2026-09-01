---
type: Defect
resource: src/graphrag/store.py
title: Reclaim never reclaimed a page
description: "`PRAGMA auto_vacuum` read 0 on 373 of 375 stores, so `PRAGMA incremental_vacuum` did nothing on any of them. The Gen-2 PHP app held 151 MB over about 9.7 MB of live data. The pragma takes only on a database whose header is not yet written, and every store older than the line ignored it."
tags: [sqlite, storage, vacuum]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: connect
    resource: src/graphrag/store.py
  - id: reclaim
    resource: src/graphrag/store.py
---

# What is wrong

`store.connect` sets `PRAGMA auto_vacuum=INCREMENTAL`[^connect]. SQLite applies that pragma only to
a database whose header has not been written yet. Every store created before the line existed keeps
`auto_vacuum=0`, and the setting is silently ignored on each later open.

`store.reclaim` runs `PRAGMA incremental_vacuum`[^reclaim]. On an `auto_vacuum=0` database that
statement does nothing at all. It does not error, and it does not warn.

# The census that proved it

Read over the whole store directory, 2026-09-01:

| Reading | Count |
|---|---|
| Stores read | 375 |
| `PRAGMA auto_vacuum` reads 0 | 373 |
| `PRAGMA auto_vacuum` reads 2 | 2 |

The Gen-2 PHP app was 151 MB holding about 9.7 MB of live data, which is 93.6% free.
The largest enrolled project was 87.5% free. So `reclaim` had never returned a page on any of the 373.

# What fixed it, and why no code changed

`config.EXTRACTION_ALGORITHM` moved from 3 to 4. `store.incompatible` wipes a store on first open
when the algorithm moves, and `store.wipe` unlinks the file. The next `connect` creates a fresh
database, and the pragma takes before the header is written. So the fix rode a change made for
another reason, and it is verified by reading the pragma rather than by a diff.

`T-277` holds it: a store this engine creates reads `PRAGMA auto_vacuum` as 2.

# The problem the fix created

`reclaim` also runs `PRAGMA wal_checkpoint(TRUNCATE)`, which is fsync-bound. It was harmless twice
over while it ran: passes were rare, and the vacuum was a no-op. After the per-file pass a pass runs
on every save, and after the rebuild the vacuum is real. So `reclaim` left the per-file path and
runs on the whole-tree pass only. `T-276` holds that, and the SCIP overlay was later moved for the
same reason: see [the overlay ran on every save](the-overlay-ran-on-every-save.md).

[^connect]: `store.connect`, the `auto_vacuum` pragma and the comment above it.
[^reclaim]: `store.reclaim`.
