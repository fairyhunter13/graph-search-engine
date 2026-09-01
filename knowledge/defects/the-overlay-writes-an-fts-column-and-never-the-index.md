---
type: Defect
resource: src/graphrag/scip/ingest.py
title: The overlay writes an FTS column and never the index
description: "`_upgrade_node` updates `qualified_name`, which `nodes_fts` indexes, and the overlay can insert nodes. There is no FTS trigger, so neither write reaches the index. It is correct today only because `index.py` runs the overlay one line before `rebuild_fts`."
tags: [scip, fts, indexing]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: upgrade
    resource: src/graphrag/scip/ingest.py
  - id: order
    resource: src/graphrag/index.py
---

# What is wrong

`nodes_fts` is an external-content FTS5 table with no trigger of any kind, and `store.py` states the
contract. `_upgrade_node` runs `UPDATE nodes SET ... qualified_name = ...`, and the overlay can
insert nodes[^upgrade]. Neither write reaches the index by itself.

Both are corrected today by ordering alone: the overlay runs one line before `rebuild_fts` in the
pass[^order]. Nothing states that dependency, and no test holds it.

# Why it is recorded and not fixed

The pass that would expose it is the per-file rewrite, which drops the wholesale rebuild. That work
is not in this commit. `rebuild_fts` stays callable and the overlay keeps running before it, so the
defect is latent rather than live. It is written down so the per-file rewrite does not rediscover it
on a stale search hit.

# The symptom to expect

A `find_symbol` hit that resolves to nothing, or a symbol SCIP renamed that is still findable only
under its old name. A stale FTS index looks exactly like a working engine, which is why this needs a
record rather than a memory.

[^upgrade]: `_upgrade_node` in `src/graphrag/scip/ingest.py`.
[^order]: The overlay call and `rebuild_fts` in `index.index_once`.
