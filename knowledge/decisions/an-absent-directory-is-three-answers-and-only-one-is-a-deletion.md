---
type: Decision
resource: src/graphrag/prune.py
title: An absent directory is three answers and only one is a deletion
description: "inotify has no replay, so a repository deleted while the daemon was down is invisible forever. The cold-start reconciliation reports rather than acts, and answers four ways: the recorded st_dev is what separates a deleted repository from an unmounted volume."
tags: [registry, prune, fleet, operations]
status: stable
generated: { by: claude/opus-5, at: 2026-08-31T00:00:00Z }
sources:
  - id: prune
    resource: src/graphrag/prune.py
  - id: entry
    resource: src/graphrag/entry.py
  - id: registry
    resource: src/graphrag/registry.py
---

# The blind spot

[a row leaves on a delete event and never on a scan](a-row-leaves-on-a-delete-event-and-never-on-a-scan.md) holds only while the daemon is up. inotify has
no replay: a repository removed during a restart, a reboot or a crash fires no event anyone will
ever see, and its row and its graph both stay forever. That is the one case the event path cannot
reach, and it is why `graphrag status` now carries a `missing` report at all — it had none, and
listed rows, failures and unclaimed stores while saying nothing about a row whose directory was
gone.

# Why `looks_deleted` is not enough here

The event path's parent test says: the path is gone and its parent is not, so the volume is still
there and the repository went. On a cold start that test is wrong in one specific case, and it is
the case the fleet wipes were made of.

A mount point is an ordinary directory when nothing is mounted on it. Unmount a volume and the
directory stays, empty, on whatever filesystem holds its parent. A row underneath it is then a
missing path whose parent exists — the exact shape of a deleted repository.

# The device is what separates them

Every claim records the `st_dev` of the path it enrolled.[^entry] The verdict compares that against
the device answering the row's nearest surviving ancestor today.[^prune] A different filesystem
answering the same path means the volume moved, not that the repository went.

Four answers, and only `deleted` is actionable:

| verdict | what it means |
|---|---|
| `present` | the directory is there |
| `deleted` | absent, an ancestor survives, and the same filesystem still answers it |
| `unmounted` | a different device answers the ancestor, or no ancestor survives at all |
| `unknown` | the row carries no recorded device, so this cannot tell |

`unknown` is the honest answer for every row written before the field existed, and it is also the
default the field falls back to. A reaper that cannot tell leaves the row alone.

# Report-only, and why that is the whole of it

`survey` reads and never writes.[^prune] The two engines' fleets were emptied twice by code that
computed a set and acted on it, and the registry's own rule is that no predicate prunes a
row.[^registry] A report is not a predicate pruner: a person reads it and types `graphrag forget`.
Making it act is a separate decision that would need its own evidence.

The hazard is not hypothetical on the machine this runs on: `~/OneDrive` and `~/GoogleDrive` are
live FUSE mounts. No indexed root sits on one today, which is exactly why the guard is written and
tested now rather than after one does.

[^prune]: `verdict` and `survey` in `src/graphrag/prune.py`.
[^entry]: the `dev` field on `ProjectEntry` in `src/graphrag/entry.py`, written by `claim` in `src/graphrag/registry.py`.
[^registry]: the module docstring and `forget` in `src/graphrag/registry.py`.
