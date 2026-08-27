---
type: Constraint
resource: src/graphrag/reach.py
title: An unreachable daemon and an absent edge look identical, and mean opposite things
description: "A session that reads a missing structural answer as nothing calling the symbol produces a confidently wrong result. The notice and the tools each say which of the two happened."
tags: [reach, daemon, degradation, honesty]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T07:08:13Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T09:53:01Z }
sources:
  - id: notice
    resource: src/graphrag/reach.py
  - id: units
    resource: src/graphrag/systemd.py
---

# The two failures a reader cannot tell apart

A caller question that comes back with nothing has three causes, and they are not the same fact.
The symbol has no callers. The language emits no call capture, so the graph never held the edge.
Or the daemon is down and no graph was consulted at all.

A registered client pointing at a dead port looks correct in every configuration file. Only a call
tells the two apart, so the notice makes the call rather than reading the config.[^notice]

# So each cause is said out loud

The unreachable variant names the port and says structural questions are unanswered this session.
The capability line names, up front, which languages here answer a caller question and which emit no
call capture. A session that learns both before it asks never reads silence as an absence.

# Why `Type=notify` belongs to the same problem

A unit that reports started as soon as the process forks turns a working install into the
unreachable case for the first few seconds of every boot.[^units] The daemon sends READY after the
worker runs and the queue is served, so started means answerable and the race does not exist.

# What would have to be true to revisit this

A transport that fails loudly and distinguishably at the call site, so a tool answer could carry the
cause without the notice having gone first. Nothing about a dead TCP port does that today.
