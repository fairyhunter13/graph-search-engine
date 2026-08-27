---
type: Constraint
resource: src/graphrag/scip/run.py
title: Every SCIP indexer needs a resolved build and tree-sitter needs none
description: "A SCIP index needs the project's dependencies resolved and its build working, and a tree-sitter parse needs only the bytes of one file."
tags: [scip, tree-sitter, build, overlay]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T10:24:21Z }
sources:
  - id: scip-run
    resource: src/graphrag/scip/run.py
  - id: extract-module
    resource: src/graphrag/extract.py
---

# The asymmetry

Tree-sitter parses one file from its bytes. No dependency is installed, no compiler runs, and a
broken file costs one file[^extract-module].

Every SCIP indexer needs the opposite. It needs the project's dependencies resolved and its build
working, because the precision comes from the type information that build produces[^scip-run].

# What that costs an operator

Some indexers can be invoked directly, and the capability table carries their argv. Others cannot.
`scip-java`, `scip-clang`, `scip-ruby` and `scip-php` carry no command, because no flag set makes a
Gradle project index itself[^scip-run].

An empty command is not a gap in the table. It means the operator runs their own build and hands the
index over. That is the only honest default for a tool that needs one.

# Why this decides the tier order

A base tier has to run everywhere, on any checkout, with no build. Only tree-sitter does that. A tier
that fails on an unbuilt project cannot own the census, so SCIP becomes the overlay. See
[the overlay decision](../decisions/scip-is-an-overlay-and-never-the-extractor.md).

# What the runner returns

The file, never the exit code. A tool that exits 0 and writes a collapsed index is the documented
failure, and the coverage guard is what catches it[^scip-run]. See
[the scip-python defect](../defects/scip-python-drops-references-and-exits-zero.md).

[^scip-run]: The module docstring, the `command` field of `Indexer`, and `run` in `src/graphrag/scip/run.py`.
[^extract-module]: The per-file extraction path in `src/graphrag/extract.py`.
