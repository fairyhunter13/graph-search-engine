---
type: Decision
resource: src/graphrag/prune.py
title: A row leaves on a delete event and never on a scan
description: "The registry refused to prune a missing path, because an unmount and a deletion look the same to a scan. They do not look the same to a delete event, so removal became automatic on the event, behind a parent test and a grace period."
tags: [registry, watcher, fleet, federation]
status: stable
generated: { by: claude/opus-5, at: 2026-08-30T00:00:00Z }
sources:
  - id: prune
    resource: src/graphrag/prune.py
  - id: watch
    resource: src/graphrag/watch.py
  - id: registry
    resource: src/graphrag/registry.py
---

# The rule this replaces, and what it was right about

`registry.py` refused to prune any row for a missing path. The argument was that an unmounted
volume, a repository moved for ten seconds and a member behind a broken symlink all look identical
to a deleted project. It was bought with an incident: a prune by predicate emptied a fleet when a
volume went away.[^registry]

Every word of that holds — **of a scan**. A scan sees a state and has to guess how it was reached.

# What a delete event knows that a scan does not

The trigger here is one `deleted` notification on the path itself, and nothing else starts a
removal.[^watch] Three tests then run, and a row dies only when all three agree.[^prune]

1. The event fired on that path. No sweep of the disk begins a removal.
2. The parent directory still exists. A repository removed leaves its parent standing. An unmounted
   volume takes the parent with it. That one test separates the two cases the old rule called
   identical.
3. A grace period passes and the path is still gone at the end of it. A `git clone` into a
   moved-aside path, and any remove-then-restore, settles well inside 30 seconds.

# The link case is weaker on purpose

A member reaches this workspace through a symlink, and the link is usually what is removed while the
target lives on. No event ever fires on the target, so the link's own deletion is the only signal.

It triggers a re-discovery of that root, and every member the walk no longer finds has that root's
claim released. `release` drops **one** claim and deletes the row only when nothing else claims it.
That is far weaker than the prune that emptied a fleet, which dropped rows by predicate. A member
two roots reach keeps its row. A member enrolled directly keeps its row.

So the report distinguishes them: `unclaimed` is the claim dropped, and `forgotten` is the row gone.

# Why the watcher owns this and not a timer

The watcher is already awake, already holds an inotify watch on every enabled project, and already
yields on a timeout. It is the one component that sees a deletion at the moment it happens. A timer
would have to scan, and a scan is the thing this decision refuses.

# Why both engines carry it

The two engines must reach the same member set. A removal rule in one engine only makes the sets
diverge the first time a repository is removed.

# What this does not clear

inotify has no replay, so a row for a project deleted while the daemon was down is never seen. That
still needs one explicit reconciliation, and `forget` is still the tool for it.

[^prune]: `looks_deleted`, `Pruner.note_gone`, `Pruner.note_unlinked` and `Pruner.run_due` in `src/graphrag/prune.py`.
[^watch]: `_register_paths`, `_keep` and `_note_deletions` in `src/graphrag/watch.py`.
[^registry]: `forget` and `release` in `src/graphrag/registry.py`.
