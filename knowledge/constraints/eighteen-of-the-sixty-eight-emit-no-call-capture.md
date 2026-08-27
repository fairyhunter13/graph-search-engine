---
type: Constraint
resource: src/graphrag/grammars.py
title: 18 of the 68 tagged grammars emit no call capture, so capability is per capture
description: "50 of the 68 tagged grammars capture a call and 18 do not, so a tags file and a caller answer are different questions."
tags: [tree-sitter, capability, calls, pin]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T10:24:21Z }
sources:
  - id: grammars-module
    resource: src/graphrag/grammars.py
  - id: grammars-test
    resource: tests/test_grammars.py
---

# The number, and the two tables it comes in

Measured under the pin on 2026-08-27. The pack census counts what the wheel ships. Of the 68 tagged
grammars, 67 capture a definition, 50 capture a call, and 17 capture an
implementation[^grammars-test]. So 18 tagged grammars answer no caller question at all. C, Swift,
TypeScript and TSX are among them.

The effective table is what this project answers with, and it reads 52 for calls. TypeScript and TSX
gain calls from the JavaScript query they concatenate. Both tables are asserted, because they answer
different questions[^grammars-test].

An earlier draft of this claim said 23. That figure was wrong, and 18 is the measured one.

# Why a language tier would be a lie

A tier says "this language is supported". The evidence does not come in language units. It comes in
capture units, and one grammar can hold definitions with no calls, or calls with no
implementations. Svelte is the sharpest case: it is tagged, and it captures no definition at all,
because its query names document sections rather than symbols[^grammars-test].

# What the engine does instead

`capabilities` returns a set per language, read from the query text. Six names are legal, and a name
outside that set is a bug rather than a language feature[^grammars-module].

Where a capability is absent, `missing` returns the sentence an answer prints. Every gap has its own
wording, so a caller reads why the answer is empty. A missing call capture says that no caller
question is answerable. That is not the same as saying that nothing calls the symbol.

# Trust and freshness

Both counts move with the pin. `T-06` asserts the pack census and the effective table together, so
an upgrade that changes either fails the suite.

[^grammars-module]: `CAPABILITIES`, `GAP_REASON`, `capabilities` and `missing` in `src/graphrag/grammars.py`.
[^grammars-test]: `test_capability_counts_under_the_pin` and `test_typescript_gains_calls_and_c_never_does` in `tests/test_grammars.py`.
