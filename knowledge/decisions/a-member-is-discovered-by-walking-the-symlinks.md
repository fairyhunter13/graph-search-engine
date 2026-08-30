---
type: Decision
resource: src/graphrag/federation.py
title: A member is discovered by walking the symlinks under the root, and declaration adds to it
description: "This engine declared its members until 2026-08-30. A workspace reaching ~360 repos through a symlink tree drifts on the first repo added, so discovery replaced declaration and federation_exclude replaced the operator's veto."
tags: [federation, scope, registry, workspace]
status: stable
generated: { by: claude/opus-5, at: 2026-08-30T00:00:00Z }
sources:
  - id: federation
    resource: src/graphrag/federation.py
  - id: config
    resource: src/graphrag/projcfg.py
  - id: coderag-federation
    resource: https://github.com/fairyhunter13/rag-search-engine
---

# What changed, and what argued against it

Until 2026-08-30 this engine took its members from `members:` in `.graphrag.yaml`, and the semantic
engine discovered them by walking symlinks.[^coderag-federation] The reason recorded here was that
this engine answers about a named symbol, so every member widens the candidate set for that name,
and an undeclared member lowers the confidence of an edge behind the operator's back.

That reason was not wrong. It was outweighed.

# Why declaration lost

The workspace this engine serves reaches about 360 repositories through a tree of symlinks, and the
tree changes whenever a repository is added. A declared list is correct on the day it is written and
wrong on the next one. What the old rule protected against is a member arriving unasked. What it
produced instead is a graph holding none of them, and a question about any of those repositories
answering nothing.

A second reason binds this engine to the other. The two must reach the same set, because a semantic
hit's path is the `root` the next structural call names. A repository in one engine and not the
other breaks that hand-off silently, and the caller reads the gap as "nothing calls this". Two
discovery algorithms that differ cannot hold that equality. One algorithm, run twice, can.

# The mechanism

`links` walks the root with `os.walk(followlinks=False)`, bounded at four levels, and resolves every
symlink it meets with `strict=True`.[^federation] A link is never descended into: its target is
enrolled as a project of its own, so walking through it would file its files under this root. The
result is deduplicated by resolved target, because this tree reaches one repository under several
names.

`members:` survives beside the walk and adds to it. A project no symlink reaches can still be named.

# What replaced the operator's veto

`federation_exclude` in `.graphrag.yaml`.[^config] It is matched against the link path **and** the
resolved target, because a layout pattern like `*/_worktrees/*` describes only the target. Matching
the link alone re-admits every second checkout of a repository the root already reaches under its
own name — 59 of them in this workspace, which the semantic engine measured at 24.8% of everything a
federated query scanned.

So the operator still chooses, and the choice is a pattern over a tree rather than a list of paths.
A pattern survives the next repository. A list does not.

# One level, and the reason it is not a depth limit

Unchanged. A member's own members belong to that member. Following them makes the reachable set a
function of what the far repository declares, which is a set nobody here chose.

# Where a discovered member becomes a row

[The registration surface](the-registration-surface-is-a-claim-and-a-row-leaves-only-on-request.md)
records the claim. A symlink is a discovery mechanism and never a key: every path handed to the
registry, the store and the watcher is the resolved target, because inotify does not traverse a
symlink and fails silently when asked to.

[^federation]: `links`, `discover`, `members_of`, `register` and `sweep` in `src/graphrag/federation.py`.
[^config]: `federation_exclude` and `exclude` in `src/graphrag/projcfg.py`.
[^coderag-federation]: `discover` and `_excluded` in the semantic engine's `src/coderag/federation.py`.
