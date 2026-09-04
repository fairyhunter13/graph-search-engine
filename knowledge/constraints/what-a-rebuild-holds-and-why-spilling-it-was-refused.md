---
type: Constraint
resource: src/graphrag/symtab.py, src/graphrag/index.py, src/graphrag/resolve.py
title: A rebuild holds the whole repo, and 374 of 380 stores are too small for that to matter
description: "A forced pass holds every file's facts at once: 120 MB for the 1786-file corpus, about 291 bytes per extracted record. Spilling `SymbolTable.files` to disk was proposed and refused on the population — the median store is 131 files and about 11 MB, and `table.files.get(path)` fires once per reference, 510,127 times on the one store that would gain."
tags: [memory, indexing, resolution, refused]
status: stable
generated: { by: claude/opus-5, at: 2026-09-04T00:00:00Z }
sources:
  - id: symtab-module
    resource: src/graphrag/symtab.py
  - id: index-module
    resource: src/graphrag/index.py
  - id: resolve-module
    resource: src/graphrag/resolve.py
---

# What a pass holds

`index.py` extracts every target file before the write transaction opens, and `symtab.build` turns
that dict into the table. A `force` pass sets `whole = True`, so a full rebuild holds the whole
repository's definitions, references and imports in memory at once. Nothing but repository size
bounds it.

Measured on the 1786-file corpus the suite already carries, reading `RssAnon` from
`/proc/self/status`:

| stage | RssAnon | VmHWM |
|---|---|---|
| start | 9 MB | 22 MB |
| every file extracted | 129 MB | 144 MB |
| the table built | 138 MB | 153 MB |

74,839 definitions, 343,796 references and 13,496 imports. So the extraction output is about
**120 MB**, or **291 bytes per extracted record**, and the `by_name` index over 44,394 names adds
**9 MB** on top of it. The two are a 13-to-1 split, and the small half is the one that has to stay
whole: a global name resolves against every file.

# Spilling `files` to disk was proposed, and the population refuses it

The obvious change is to keep `by_name` in memory and read `files` one path at a time. The resolve
loop takes one path per iteration and keeps nothing across them, so the shape fits.

Two measurements say not to. Both are about who actually pays.

**The stores are small.** Over all 380 graphs on this host:

| | files per store |
|---|---|
| p50 | 131 |
| p95 | 795 |
| max | 11,722 |

At 291 bytes per record the median store peaks near **11 MB**. Only **6 of 380** are larger than
the corpus measured above. The largest holds 99,303 nodes, 510,127 references and 7,996 imports —
617,426 records, so about **171 MB**, once, on a forced rebuild. The daemon's steady state is
227 MB after seven days, and that number is near the floor for a Python process holding 371
tree-sitter grammars.

**The lookup is per reference, not per file.** `resolve_file` calls `resolve_reference` for every
reference in the file, and `resolve_reference` reaches `_enclosing_class`, which calls
`table.files.get(path)`. So the mapping is read **once per reference**: 343,796 times on the
measured corpus and 510,127 times on the one store a spill would help. A disk-backed mapping there
trades transient memory for CPU in the hottest loop in the engine, and the ask that raised this was
to lower both.

A one-entry cache would answer nearly all of those reads, because every inner lookup names the path
the outer loop is already on. That is true and it is not enough: `indexwrite` walks `table.files`
twice more, four modules read the attribute, and the whole apparatus buys 171 MB on 1 project of
380 and about 11 MB on the median one.

# What would reverse this

A store past roughly 30,000 files, or a host where the indexer runs against a memory limit rather
than against 63.7 GB. Either one moves the largest figure above the daemon's steady state and makes
the trade a real one. Until then the smallest sufficient change here is no change.

The related refusal on the sibling engine is its own indexing card: six CPU arms measured, all
lost. Neither engine has an indexing lever left that evidence supports.
