---
type: Decision
resource: src/graphrag/quarantine.py
title: A dead row takes its graph, and the delete is a move
description: "Removing a row freed no disk at all: the graph stayed until a human typed a prune. The reaper now takes the graph too, behind an idle floor, and it moves it into a week-long quarantine rather than deleting it."
tags: [registry, prune, storage, fleet]
status: stable
generated: { by: claude/opus-5, at: 2026-08-31T00:00:00Z }
sources:
  - id: quarantine
    resource: src/graphrag/quarantine.py
  - id: prune
    resource: src/graphrag/prune.py
  - id: registry
    resource: src/graphrag/registry.py
  - id: cli
    resource: src/graphrag/cli.py
---

# The asymmetry this closes

[a row leaves on a delete event and never on a scan](a-row-leaves-on-a-delete-event-and-never-on-a-scan.md) made the row automatic and left the bytes
manual. The watcher dropped the row on the delete event; the graph directory stayed on disk, became
*unclaimed*, and waited for someone to type `graphrag prune --apply`. Measured across the two
engines on 2026-08-31: 197 unclaimed stores in the semantic engine, 748 MB, and two here. Nothing
in either engine returned a byte without a human command.

`run_due` now retires the graph of every row it forgets.[^prune] The trigger is unchanged — one
delete event, a parent test and a grace period — so this adds no predicate and no scan.

# Two guards, one of which did not exist

**The idle floor.** `PRUNE_MIN_IDLE_S` was declared at the rebuild and read by nothing, so it was
built here rather than switched on: a graph written inside the floor is left where it is and the
report says so.[^prune] The semantic engine has the incident recorded — a prune raced a store the
daemon was mid-write on — and moving the removal onto an automatic path is exactly when that
recurs.

**The shape of the answer.** `prune_unclaimed` refuses a verdict against an empty registry outright,
and one covering more than half the tree without `--force`.[^registry] `--force` deliberately does
not lift the empty-registry refusal: a registry that failed to load looks exactly like a fleet with
nothing enrolled, and that is the shape both fleet wipes had. Ported from the semantic engine, whose
own version was bought with them.

# Why a move and not a delete

Both wipes surfaced days late and the same way: someone searched a repository and got nothing back.
A store a person removed by hand has a witness at the moment it goes. One an automatic path removed
has none.

So the reaper renames the directory into `INDEX_DIR/.trash/<unix-ts>-<name>` and deletes it seven
days later.[^quarantine] Three rules hold it:

- **A failed rename never becomes an `rmtree`.** The store stays where it stands and the caller
  reports a store it did not remove. A path whose whole purpose is undo cannot answer a failure by
  deleting harder.
- **`.trash` is not an unclaimed store.** No row names it, so the orphan walk would otherwise list
  it, delete it on the next pass, and report the undo as reclaimed waste.[^registry]
- **A name the quarantine did not write is left alone.** Expiry parses its own timestamp prefix and
  skips anything else rather than guessing.[^quarantine]

`forget` quarantines too, and that closes [prune wiped the graph but kept the directory](../defects/prune-wiped-the-graph-but-kept-the-directory.md) on its
last surface: `forget` used to call `wipe`, which unlinks the database and leaves the directory
standing for the orphan count to keep finding. A rename takes the directory with it.[^cli]

# What this still does not clear

inotify has no replay, so a repository deleted while the daemon was down reaches no event. That is
reported and never acted on — see [an absent directory is three answers and only one is a deletion](an-absent-directory-is-three-answers-and-only-one-is-a-deletion.md).

[^quarantine]: `take` and `expire` in `src/graphrag/quarantine.py`.
[^prune]: `_is_idle`, `_retire_stores` and `Pruner.run_due` in `src/graphrag/prune.py`.
[^registry]: `_stale_unlocked` and `prune_unclaimed` in `src/graphrag/registry.py`.
[^cli]: `cmd_forget` and `cmd_prune` in `src/graphrag/cli.py`.
