---
type: Constraint
resource: src/graphrag/extract.py
title: A member call is about 43% of call sites, and a syntactic rule cannot reach it
description: "About 43% of call sites are member calls, and no syntactic rule places the receiver, so the engine refuses those sites rather than guessing."
tags: [extraction, resolution, calls, limits]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T10:24:21Z }
sources:
  - id: extract-module
    resource: src/graphrag/extract.py
  - id: resolve-test
    resource: tests/test_resolve.py
---

# The shape and the share

`expr.method()` is about 43% of call sites[^extract-module]. The extractor keeps the separator and
the receiver name, because the receiver is what tells `registry.load()` from `yaml.load()`. Keeping
only the attribute name makes those two one name in the graph.

# Why the receiver is often out of reach

A receiver that names a module is a fact, and the resolver narrows the pool with it. A receiver that
names a local variable is not. Placing it needs the type of that variable, and no query over a
syntax tree carries a type.

So the rule steps aside for `self`, `this` and their siblings, where the class and file tiers
already price the call. For the rest it refuses rather than guessing[^extract-module].

# The cost, measured

On the pinned corpus the scoped arm refuses between 30% and 55% of call sites, and the assertion
bands the share rather than fixing it[^resolve-test]. A share far under the band means the receiver
rule stopped firing. A share far over it means the rule started eating calls it could resolve.

The price is sites, not recall. A refused site produces no edge, and it never produces a wrong one.

# What closes the gap, and what does not

Nothing syntactic closes it. The SCIP overlay does, where an indexer is available, because a
resolved build knows the type of the receiver. See
[the overlay decision](../decisions/scip-is-an-overlay-and-never-the-extractor.md).

The same limit is what keeps the class split open in
[the routing measurement](../computations/the-graph-answers-the-caller-question.md).

[^extract-module]: The comment on the member separator in `src/graphrag/extract.py`, and the `receiver` field on `Reference`.
[^resolve-test]: `test_import_scoping_collapses_candidates` in `tests/test_resolve.py` asserts the refused share inside a band.

# The design this share prices

[The resolution decision](../decisions/resolution-is-import-scoped-and-ranked-and-never-forced.md)
is what refuses these sites, and it names the tiers that price the rest.
