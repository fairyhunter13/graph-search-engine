---
type: Decision
resource: src/graphrag/federation.py
title: A member is declared in the project config and never discovered by a walk
description: "The semantic engine finds members by walking symlinks under the root. A graph engine will not, because an undeclared member adds candidate definitions the operator never chose."
tags: [federation, scope, registry, workspace]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T07:04:49Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T09:53:01Z }
sources:
  - id: coderag-federation
    resource: https://github.com/fairyhunter13/rag-search-engine
  - id: config
    resource: src/graphrag/projcfg.py
---

# What the two engines each need from a member set

The semantic engine ranks over a corpus, so a member that arrives by accident widens recall and
costs nothing else. Discovery by symlink is the right mechanism there, and it is what it
runs.[^coderag-federation]

This engine answers about a named symbol. Every member it reaches contributes definitions to the
candidate set for that name, so an undeclared member silently lowers the confidence of an edge the
operator believes is a fact. The set has to be something a person chose and can read back.

# So the config is the whole of the set

`members` in `.graphrag.yaml` names the directories, and nothing else adds one.[^config] A path
that is absent is dropped rather than raised, because a member on an unmounted disk is absent and
not wrong. That is the registry rule about a missing path, applied to the declaration.

# One level, and the reason it is not a depth limit

A member's own members belong to that member. Following them makes the reachable set a function of
what the far repository declares, which is a set nobody in this repository chose. A depth ceiling
would bound the cost of the walk and leave the ownership problem exactly where it was.

# What would have to be true to revisit this

A workspace where the same members are declared in every project, and the duplication is the thing
operators complain about. Discovery would then be removing a chore rather than widening a candidate
set behind their backs.
