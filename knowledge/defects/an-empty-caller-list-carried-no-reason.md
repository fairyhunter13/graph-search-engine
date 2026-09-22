---
type: Defect
resource: src/graphrag/query.py
title: An empty caller list carried no reason, on a corpus that holds 17 references to the name
description: "A caller question walks back through resolution, so a reference the resolver cannot place is never counted. The answer was an empty list with a capability report that named no gap, which is the confidently wrong answer this engine's own module docstring says it exists to avoid."
tags: [resolution, honesty, gaps, go]
status: stable
generated: { by: claude/opus-5, at: 2026-09-22T12:40:38Z }
sources:
  - id: query
    resource: src/graphrag/query.py
  - id: case
    resource: tests/test_index.py
  - id: sibling
    resource: knowledge/defects/a-start-with-four-homonyms-answered-for-one.md
---

# What it did

A private Go repository declares one method name on four receivers and calls it through a
field, in the shape `svc.Field.Method(...)`. The corpus is not named here and neither is the
method: `policies/private-evidence-is-a-measurement-not-an-identifier.md` is the rule, and the
counts below are the whole of the evidence.

The store holds 17 `refs` rows spelling that one name, which is every call site a text search
finds. `neighbors(..., "callers")` returned an empty list for all four declarations, and the
only gaps were the four languages with no call capture. `include_ambiguous=True` changed
nothing, because the declaration is never a candidate: a receiver's type is not resolved to
the package that declares the method, so the resolver has nothing to place.

The emptiness was correct as an edge count and wrong as an answer. `query.py` opens with the
rule it broke: an empty list "reads as 'nothing calls this', which is the confidently wrong
answer this engine exists to avoid".

# What it does now

An upstream answer counts the `refs` rows that spell the start's name, and reports how many
of them reached this definition. On that corpus it read, with the name elided:

> 17 references in this project spell '...' and 0 of them resolved to this definition, so
> this answer understates.

The count is the whole of it. Zero beside zero is a real absence. Zero beside seventeen is a
resolution gap, and the reader can see which one they have without opening the store.

The gap is upstream only. A callee question reads the references a body makes, so a count of
every reference that spells the start's own name says nothing about it.

# What it does not fix

The Go receiver is not resolved. That is the cause, and this concept does not close it: the
gap reports the shortfall rather than recovering the edges. Closing it needs a receiver type
to reach a package, which is the same shape as
`defects/module-identity-is-python-shaped.md` and belongs with it.

`T-346` holds the reporting. Its corpus calls a method on a parameter, so the receiver's type
is unknown and the reference resolves to nothing. A same-file call would not serve: that is
stored as an edge and writes no `refs` row, so there would be no unreached reference to count.
