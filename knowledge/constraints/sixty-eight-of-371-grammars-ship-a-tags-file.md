---
type: Constraint
resource: src/graphrag/grammars.py
title: 68 of 371 grammars ship a tags file, so any language means parsing and not symbols
description: "The pack parses 371 languages and only 68 carry a tags query, so a grammar with no tags file yields a tree and no symbol."
tags: [tree-sitter, capability, coverage, pin]
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

# The number

Measured under the pin on 2026-08-27: the pack manifest lists 371 grammars, and 68 of them return a
non-empty `tags.scm`[^grammars-test]. The other 303 parse and extract nothing.

# Why the gap exists

A grammar gives a syntax tree. A tags query is a separate artifact that says which node in that tree
is a definition and which is a reference. Upstream tree-sitter never required one, so most grammars
ship without it, and no amount of parser work fills the gap.

# What this forbids in an answer

The engine must never state a language count that comes from the manifest. "371 languages" is a
parsing claim. The symbol claim is 68, and a query answer that conflates the two promises coverage
the store does not hold.

The capability table is read from the query text, which the wheel carries. No parser download is
needed to answer it, so `doctor` reports the table offline[^grammars-module].

# What this constraint does not say

It does not say the 68 all answer the same question. Capability is per capture, and the finer split
is in
[the call-capture constraint](eighteen-of-the-sixty-eight-emit-no-call-capture.md).

# Trust and freshness

The two counts move with the pin, and only with the pin. `T-06` asserts both, so an upgrade that
changes either fails the suite rather than drifting into prose.

[^grammars-module]: `known_languages`, `capabilities` and `capability_table` in `src/graphrag/grammars.py`.
[^grammars-test]: `test_capability_counts_under_the_pin` in `tests/test_grammars.py` asserts 371 and 68 on pack 1.15.8.

# Two records sit next to this one

[The capture vocabulary decision](../decisions/the-capture-vocabulary-is-the-maintainers-and-the-pin-is-exact.md)
says who writes the names in those 68 files.
[The pack install constraint](the-pack-ships-queries-and-downloads-parsers-on-first-use.md) says why
reading them needs no network.
