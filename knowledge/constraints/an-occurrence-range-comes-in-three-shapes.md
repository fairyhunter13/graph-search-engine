---
type: Constraint
resource: src/graphrag/scip/read.py
title: An occurrence range comes in three shapes, and scip-java emits only the newest
description: "SCIP v0.8.0 deprecated the flat integer range for a typed one, and scip-java emits only the typed form, so a one-shape reader gets nothing."
tags: [scip, wire-format, compatibility, reader]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
sources:
  - id: scip-read
    resource: src/graphrag/scip/read.py
  - id: scip-read-test
    resource: tests/test_scip_read.py
  - id: scip-proto
    resource: https://github.com/scip-code/scip/blob/main/scip.proto
    digest: sha256:b38021b65ef90cbbf6af9c829ff75192859ad9b5da05439ef154bea4ceb2bf03
---

# The three shapes

An occurrence carries its position in one of three encodings[^scip-proto]. The deprecated one is a
flat repeated integer field, three elements for a single-line range and four for a multi-line one.
The typed one is two messages, one single-line and one multi-line.

v0.8.0 deprecated the flat field. `scip-java` v0.13 emits only the typed
form[^scip-read-test].

# Why this is not a normal compatibility problem

A missing field on the wire is not an error. Take a reader written for the deprecated field alone.
It reads a `scip-java` index and finds no range on any occurrence. It returns an index with zero
usable positions. Nothing raises, and the failure looks like an empty project.

# What the reader does

It collects all three and prefers the typed form where both are set[^scip-read]. A flat field with a
length other than three or four is not a range, so it yields nothing rather than a guess.

# What grades it

`T-17` writes all three shapes by hand and asserts one span from each. It also asserts the
multi-line deprecated case keeps its end line, and that the typed form wins a
conflict[^scip-read-test].

# The other half of a position

A range is in the units the document's encoding names, and that encoding is often unset. See
[the position-encoding constraint](an-unset-position-encoding-does-not-mean-one-thing.md).

[^scip-read]: `_typed_range`, `_deprecated_range` and `_occurrence` in `src/graphrag/scip/read.py`.
[^scip-read-test]: The module docstring and the three range tests in `tests/test_scip_read.py`.
[^scip-proto]: `Occurrence.range` and `Occurrence.typed_range` in `scip.proto`.
