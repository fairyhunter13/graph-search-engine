---
type: Decision
resource: src/graphrag/registry.py
title: A project registers by claim, keyed on its resolved path, and a row leaves only on request
description: "The fleet registry keys every row on the resolved path, counts the claims a row carries, and never prunes a row for a missing path."
tags: [registry, fleet, federation, locking]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
sources:
  - id: registry
    resource: src/graphrag/registry.py
  - id: entry
    resource: src/graphrag/entry.py
---

# The surface

`projects.json` holds one row per project, and the key is the resolved
path[^registry]. A symlink is a discovery mechanism and never a key. A relative or symlinked path
that skips resolution claims a different row, and every later answer files under the wrong root.

`claim` enrols a project or adds a claim to one already enrolled. A row records whether an operator
asked for it directly, and which other projects name it as a member[^entry]. `release` drops one
claim, and the row survives while anything else claims it.

# Why a row is never pruned by a scan

An unmounted volume, a repo moved for ten seconds, and a member behind a broken symlink all look
identical to a deleted project — to a scan. So no scan removes anything, and `forget` takes a list
of keys rather than a predicate[^registry].

A delete event is not a scan, and since 2026-08-30 one does remove a row, behind a parent-exists
test and a grace period. That is
[a row leaves on a delete event](a-row-leaves-on-a-delete-event-and-never-on-a-scan.md).

# Why removal is one write

`forget` writes once for the whole set. The backup rotation stamps to the second. A loop of
single-row removals overwrites its own backup inside that second, and the surviving restore point is
then a half-pruned registry.

# Two rules copied from the semantic engine

Both were bought with incidents there rather than reasoned out here[^registry].

The load happens inside the lock. Reading first and locking second is a lost update. Two writers each
read the rows, each add one, and the second write drops the first. It was measured once as a registry
that kept 34 of 180 rows.

`unclaimed_stores` reads the rows and globs the directory inside one lock, for the same reason. A
project claimed between the two reads would enumerate as unclaimed, and a caller acting on that
answer deletes a graph the daemon holds open.

# What the fleet digest reports, and what it hides

A hash of what every row is, not how many there are. A count is blind to a canceling pair, to a
disabled row, and to a dead root left in a live project's claims. No path is disclosed, because the
key is hashed with the rest[^registry].

# What this decision does not cover

Which directories become members of a project. That is
[the member discovery decision](a-member-is-discovered-by-walking-the-symlinks.md).

[^registry]: The module docstring, `resolve`, `claim`, `release`, `forget`, `fleet_digest` and `unclaimed_stores` in `src/graphrag/registry.py`.
[^entry]: `ProjectEntry` in `src/graphrag/entry.py`, with its `direct` and `roots` fields.
