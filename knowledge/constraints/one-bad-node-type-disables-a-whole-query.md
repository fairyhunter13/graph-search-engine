---
type: Constraint
resource: src/graphrag/queries/imports
title: One bad node type disables a whole import query, silently
description: "A tree-sitter query compiles whole or not at all, and the extractor returns no matches rather than raising. A single wrong node type makes every pattern in the file dead, and the language then reads as one with no import syntax."
tags: [tree-sitter, queries, imports, silent-failure]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T06:34:13Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
sources:
  - id: sourcepawn-case
    resource: src/graphrag/queries/imports/sourcepawn.scm
  - id: compile-case
    resource: tests/test_import_queries.py
---

# What happens

`ts.Query` parses the whole file before it matches anything. One node type the grammar does not
carry raises at construction, and `extract._run` catches every exception and returns an empty
list.[^sourcepawn-case] So the patterns that were correct never run either.

# Why the failure is silent

An empty import list is a legal state. 36 of the 68 `tags.scm` languages have no import query at
all, and the engine already reports that as a gap. A language that has a query and returns nothing
is indistinguishable from one that has none, and the gap notice does not fire because the query file
exists.

# How it was found

`sourcepawn.scm` named a `string_content` child of `string_literal`. That grammar has no such node,
and the whole file went dead. The extractor reported zero imports on a file holding two include
directives, with no error anywhere.

# The check that sees it

`T-56` compiles every vendored query against its own grammar and fails naming the language.[^compile-case]
Running the query over a sample is not enough on its own: a sample proves one pattern, and the
compile check proves the file.

[^sourcepawn-case]: The query that shipped the defect, now written against `system_lib_string` and `string_literal`.
[^compile-case]: `tests/test_import_queries.py::test_every_vendored_import_query_compiles`.
