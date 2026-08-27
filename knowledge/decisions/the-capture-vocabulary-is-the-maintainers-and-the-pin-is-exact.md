---
type: Decision
resource: src/graphrag/queries.py
title: The capture vocabulary belongs to the pack maintainer, so the pin is exact and a test grades every name
description: "The pack maintainer curates the tags queries, so the capture names drift with the pin, and every name is mapped or listed as ignored."
tags: [tree-sitter, vocabulary, pin, extraction]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T10:24:21Z }
sources:
  - id: queries-module
    resource: src/graphrag/queries.py
  - id: queries-test
    resource: tests/test_queries.py
  - id: pack
    resource: https://pypi.org/project/tree-sitter-language-pack/
    digest: sha256:96782bd88889418c7efdb8ab958aca2491fe510bd942a91fdb8e9bd9113cf07e
---

# The fact this decision answers

The extractor dispatches on capture names such as `definition.class` and `reference.call`. Those
names are not a standard. They come from the `tags.scm` files the language pack
curates[^pack]. The maintainer writes them, and a new release can rename one, add one or drop one.

Under the current pin the pack ships 58 distinct capture names across its 68 tags
files[^queries-module].

# The choice

Two designs were open. Map the names the extractor knows and drop the rest silently. Or pin the pack
exactly, map every name, and fail a test on any name that is neither mapped nor named as ignored.

This engine takes the second. `tree-sitter-language-pack` is pinned with `==`, not a range. Every
capture name lands in one of three sets: a definition kind, a reference edge kind, or the ignored
list. The ignored list is written out by hand, and each entry carries the reason it is
ignored[^queries-module].

# Why a silent drop was rejected

A dropped capture is not visible. The language keeps parsing, the extractor keeps returning rows, and
the graph is quietly missing an edge kind. Nothing in an answer says so. Grading the vocabulary turns
that into a red test at upgrade time, which is the only moment a human is looking.

# The test is the gate on the pin

`T-05` reads every capture name out of every tags file and asserts that the unmapped set is
empty[^queries-test]. Moving the pin without touching the maps therefore fails the suite. That is
the intended cost of the upgrade.

The name reader strips comments and string literals first. A capture name inside a `#match?`
argument is not a capture. Neither is one on a commented-out line. Reading either as vocabulary drift
would make the gate cry wolf[^queries-module].

# Where the pack query is wrong rather than merely different

A repair layer concatenates after the pack query, one file per language, and each file names the gap
it closes. PHP ships no scoped call pattern, so `User::find()` captures nothing at all. The repair
keeps the pin exact and keeps the pack unforked.

# What would have to be true to revisit this

Upstream tree-sitter publishes the tags vocabulary as a contract. Then the names stop being one
maintainer's choice, and the exact pin can relax to a compatible range.

[^pack]: `tree-sitter-language-pack` on PyPI, pinned at 1.15.8 in `pyproject.toml`.
[^queries-module]: `DEFINITION_KINDS`, `REFERENCE_KINDS`, `IGNORED_CAPTURES`, `capture_names` and `TAGS_EXTRA_DIR` in `src/graphrag/queries.py`.
[^queries-test]: `test_every_capture_name_is_known` in `tests/test_queries.py` asserts 58 names and an empty unknown set.

# Why this engine reads a tags query at all

[The founding decision](tree-sitter-is-declined-for-chunking-and-adopted-for-graphs.md) says what
this engine takes from the parser, and what the semantic sibling refused.
