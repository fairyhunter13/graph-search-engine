---
type: Decision
resource: src/graphrag/scip/__init__.py
title: SCIP is an overlay and never the extractor, because a symbol role carries no call role
description: "SCIP names an occurrence and its roles, and no role is a call, so SCIP upgrades a call site rather than finding one."
tags: [scip, overlay, extraction, tree-sitter]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T10:24:21Z }
sources:
  - id: scip-proto
    resource: https://github.com/scip-code/scip/blob/main/scip.proto
    digest: sha256:b38021b65ef90cbbf6af9c829ff75192859ad9b5da05439ef154bea4ceb2bf03
  - id: scip-package
    resource: src/graphrag/scip/__init__.py
  - id: scip-ingest
    resource: src/graphrag/scip/ingest.py
---

# The choice

SCIP indexes are precise. A tempting design lets SCIP own extraction where it is available, and
falls back to tree-sitter elsewhere. This engine refuses that. Tree-sitter owns the whole census of
files, definitions and call sites, and SCIP only upgrades rows that census already
holds[^scip-package].

# The reason is in the schema, not in a preference

`SymbolRole` is a bit set on an occurrence. It marks a definition, an import, a read, a write, a
generated site and a test site. No bit means "this is a call"[^scip-proto]. A non-definition
occurrence is therefore a name mention and nothing more.

An engine that read those mentions as calls would invent edges. A name in a type annotation, a
docstring reference and a real call all arrive as the same thing. So the ingest path rewrites a call
only where tree-sitter already recorded one at that byte[^scip-ingest].

# What the overlay is allowed to change

It replaces the ranked candidate set at a call site with the one target SCIP names, at confidence
1.0 and evidence `scip`. It upgrades a node's documentation and qualified name. It adds an
implementation edge where the indexer emits relationships. That is the whole surface.

# What silence means

SCIP saying nothing about a symbol is not evidence that no call exists. The symbol keeps its
import-scoped ranked candidates. This is the same reading rule that
[an unreachable daemon](../constraints/an-unreachable-daemon-is-not-an-absent-edge.md) states for
the transport.

# The other half of the argument

Every SCIP indexer needs a resolved build, and tree-sitter needs none. That asymmetry decides which
tier is the base and which is the overlay. See
[the resolved-build constraint](../constraints/every-scip-indexer-needs-a-resolved-build.md).

# What would have to be true to revisit this

SCIP grows a role, or an equivalent field, that marks a call site directly. Then SCIP could extract
rather than upgrade, and the base tier becomes a real choice again.

[^scip-proto]: `SymbolRole` in `scip.proto`. The reader here keeps only the `Definition` bit, at `DEFINITION = 0x1` in `src/graphrag/scip/read.py`.
[^scip-package]: The module docstring of `src/graphrag/scip/__init__.py` states the rule.
[^scip-ingest]: `_rewrite_call` in `src/graphrag/scip/ingest.py` returns False where no tree-sitter call sits at that byte.

# Two per-indexer facts a reader of this record needs

[The kind constraint](../constraints/symbol-information-kind-is-a-per-indexer-capability.md) says why
a kind of 0 must not overwrite anything.
[The range constraint](../constraints/an-occurrence-range-comes-in-three-shapes.md) says why a
one-shape reader gets nothing from scip-java.
