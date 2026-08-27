---
type: Constraint
resource: src/graphrag/scip/run.py
title: SymbolInformation.kind is a per-indexer capability, and 0 does not mean unspecified
description: "Five of the ten live SCIP indexers leave the kind field at 0, so 0 means the tool declined to answer."
tags: [scip, capability, kind, overlay]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
sources:
  - id: scip-run
    resource: src/graphrag/scip/run.py
  - id: scip-ingest
    resource: src/graphrag/scip/ingest.py
  - id: scip-proto
    resource: https://github.com/scip-code/scip/blob/main/scip.proto
    digest: sha256:b38021b65ef90cbbf6af9c829ff75192859ad9b5da05439ef154bea4ceb2bf03
---

# The field looks universal and is not

`SymbolInformation.kind` is one enum in one schema, so a reader expects every indexer to set
it[^scip-proto]. Five of the ten live indexers leave it at 0[^scip-run]. Among them are
`scip-python`, `scip-typescript`, `scip-clang`, `scip-ruby` and `scip-php`.

The capability table in `run.py` holds nine rows and carries `sets_kind` per row. `scip-dotnet` is
the tenth live tool. It appears in the encoding table and carries no capability row, so this engine
does not ingest an index it wrote.

# Why 0 is the dangerous value

The enum spells 0 as unspecified. Read literally, that is an answer, and an overlay would write it
over whatever tree-sitter found. The result is a node that had a kind before the overlay ran and has
none after it.

So the ingest path reads `kind` only where `sets_kind` is true, and it coalesces an empty result back
to the existing value[^scip-ingest]. A tool that declines to answer changes nothing.

# The same shape as the tree-sitter rule

Capability is per indexer here, exactly as it is per capture in tree-sitter. `rust-analyzer` is the
other half of the pattern: it emits no relationships at all, so a Rust trait implementation comes
from tree-sitter or from nowhere[^scip-run].

# What is left when the field is 0

The descriptor suffix on the symbol string. It is the only kind signal those indexes carry, and the
symbol parser reads it[^scip-ingest].

[^scip-run]: The module docstring and the `INDEXERS` table in `src/graphrag/scip/run.py`, with `sets_kind` per row.
[^scip-ingest]: `_upgrade_node` in `src/graphrag/scip/ingest.py`, and `_SUFFIX_KIND` in `src/graphrag/scip/symbol.py`.
[^scip-proto]: `SymbolInformation` and `Kind` in `scip.proto`.
