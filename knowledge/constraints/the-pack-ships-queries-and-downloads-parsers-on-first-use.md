---
type: Constraint
resource: src/graphrag/grammars.py
title: The pack ships its queries in the wheel and downloads a parser on first use
description: "Query text arrives with the install, and a parser arrives over the network on first use, so an air-gapped install needs a seeded cache."
tags: [tree-sitter, install, offline, cache]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
sources:
  - id: grammars-module
    resource: src/graphrag/grammars.py
  - id: pack
    resource: https://pypi.org/project/tree-sitter-language-pack/
    digest: sha256:96782bd88889418c7efdb8ab958aca2491fe510bd942a91fdb8e9bd9113cf07e
---

# Two halves of the pack arrive at different times

The wheel carries the manifest and the `tags.scm` text[^pack]. `get_parser` fetches a per-language
shared object into the user cache the first time it is asked for that
language[^grammars-module].

# What that means for a first run

An indexing run on a machine with no network reaches a language, asks for a parser, and gets
nothing. An air-gapped install therefore has to seed the parser cache from a machine that had
network. Nothing in the wheel makes that step unnecessary.

# What the engine does with the failure

`parser_for` returns None rather than raising. A project then indexes its other languages instead of
failing whole[^grammars-module]. A missing parser costs one language, and it never costs the run.

# Why the capability table is still offline

Capability is read from the query text, and the query text is in the wheel. So `doctor` reports the
whole table on a machine that has never downloaded a parser. Reporting capability and extracting
symbols have different network needs, and only the second one is online.

That is also why `known_languages` reads the manifest rather than `available_languages`. The second
lists what is already downloaded, so using it would make the capability table depend on download
history[^grammars-module].

[^grammars-module]: `known_languages`, `cached_languages` and `parser_for` in `src/graphrag/grammars.py`.
[^pack]: `tree-sitter-language-pack` on PyPI, pinned at 1.15.8 in `pyproject.toml`.
