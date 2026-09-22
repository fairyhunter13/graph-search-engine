---
type: Defect
resource: src/graphrag/query.py
title: A start with several homonyms answered for one of them and said nothing
description: "_resolve_start read find_symbol with limit=1 and took the first row, so a question about a name was answered for whichever definition FTS ranked first. ambiguous stayed 0, because it counts the candidates of each edge and not the candidates of the start."
tags: [resolution, ambiguity, mcp, honesty]
status: stable
generated: { by: claude/opus-5, at: 2026-09-22T12:40:38Z }
sources:
  - id: resolve
    resource: src/graphrag/query.py
  - id: case
    resource: tests/test_index.py
  - id: surface
    resource: src/graphrag/tools.py
---

# What it did

`_resolve_start` was two lines:

```python
hits = find_symbol(conn, symbol, limit=1)
return hits[0].node_id if hits else None
```

Two definitions spell `handle`, in `one.py` and `two.py`, and only the first is called.
`neighbors("handle", "callers")` returned the caller of the first and reported
`ambiguous: 0` with an empty `gaps`. Nothing in the answer said a second definition existed.
Had FTS ranked the other row first, the same call would have returned an empty list, which
reads as "nothing calls handle" and is false for the definition the caller may have meant.

`ambiguous` could not carry this. It counts the candidates of each edge, so a start with four
homonyms and one clean edge each reports zero. The number is about resolution of a reference,
and the start is not a reference.

# The second half: FTS is not an exact match

`find_symbol` runs FTS5 over `name` and `qualified_name`. A module node is stored as
`package:<path>`, and FTS tokenizes it, so on a private Go corpus one query matched 25 module
rows of a directory whose name shared a token, beside the 4 methods that carry the name
itself. With the default `limit` of 20 the package rows can crowd the real symbols out of the
reply, and one of them winning the start meant the answer belonged to a node the caller never
named.

An exact hit on `name` or `qualified_name` is now preferred, and the rest are kept only as a
fallback for a caller who typed a fragment.

# Why a qualified name was not enough of a remedy

Python carries the receiver in `qualified_name`, so `Alpha.handle` separates two methods.
Go does not: a method's `qualified_name` is its own name, so the four methods on four
receivers are indistinguishable by every field the reply carried. So `find_symbol` now
returns `node_id`, and `neighbors` and `blast_radius` accept one. Over MCP every argument
arrives as a string, so the surface coerces a digit string to an id; without that the gap
would name a remedy the caller could not pass.

The Go receiver is a separate gap and this concept does not close it. `qualified_name` there
is still the bare method name.

# What holds it now

`T-342` asserts the gap names both locations and that the two definitions have different
caller sets, which is what makes the silent pick a wrong answer rather than an arbitrary
one. `T-343` asserts a single definition carries no gap, so the line is a fact about the
start and not a banner. `T-344` asserts the exact-name preference. `T-345` asserts
`blast_radius` owes the same fact, because it resolves a start the same way.
