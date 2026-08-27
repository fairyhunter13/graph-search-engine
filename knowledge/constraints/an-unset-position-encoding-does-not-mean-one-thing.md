---
type: Constraint
resource: src/graphrag/scip/offsets.py
title: An unset position_encoding does not mean one thing
description: "Most indexers leave the field at 0, and 0 means UTF-8 on scip-go and UTF-16 on scip-python. So the fallback is keyed on the tool name, and an unknown name is an error rather than a guess."
tags: [scip, offsets, encoding]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T12:00:00Z }
sources:
  - id: scip-proto
    resource: https://github.com/sourcegraph/scip/blob/v0.9.0/scip.proto
---

# The trap

An occurrence range counts columns, and the unit of a column is what `position_encoding`
declares.[^scip-proto] Only three indexers declare it. `scip-go` leaves it 0 and emits UTF-8 bytes.
`scip-python` and `scip-typescript` leave it 0 and emit UTF-16, because both are TypeScript
programs counting with a JavaScript string. `scip-dotnet` and `scip-ruby` vendor a proto that lacks
the field.

So a default of UTF-8 is right for one of those and wrong for the others, and it is wrong only on
lines holding a character outside ASCII. Every offset after that character shifts, and the overlay
then writes an edge onto a node it did not mean.

# The rule

`offsets.encoding_for` returns the declared value where it is set. Where it is not, it reads a
table keyed on `tool_info.name`. A name off that table raises, and never falls back.

# What proves it

`T-18` puts a non-ASCII identifier at a known byte range and hands the same definition to two
indexers with the columns each one would emit. UTF-16 column 10 and UTF-8 column 11 must both land
on the same byte range, and nothing else catches the table being wrong.

# One more rule that lives in the same module

Lines split on `\n` alone. `str.splitlines()` also splits on `\v`, `\f`, `\x85` and two Unicode
separators, and every later line then shifts with no error.
