---
type: Decision
resource: src/graphrag/store.py
title: A silent file names its cause, and the census is what earns the column
description: "24,318 of 101,000 files across 376 stores read `tier='none'` and nothing else, and five different causes wore that one name. `files.reason` separates them from a closed set of five. The motive the column was first asked for -- a skip cache for pathological files -- is dropped, because an unchanged file never reaches the extractor. What earns it instead is that 6,301 of those files are in languages with the full capability set, silent for no recorded reason."
tags: [store, schema, diagnostics, census, extraction]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: schema
    resource: src/graphrag/store.py
  - id: tier
    resource: src/graphrag/indexwrite.py
  - id: diff
    resource: src/graphrag/discover.py
---

# The motive that was asked for, and why it is dropped

The column was requested so a file that fails to parse is not re-parsed and re-failed on every
pass. That does not survive contact with the code. `index.index_once` builds its target list from
`discover.diff`[^diff], which compares `sha256` per path. An unchanged file is not in the list, so
the extractor never runs on it and the re-parse the column was to prevent does not happen. The skip
cache went with the motive.

Recording a dropped motive is cheaper than rediscovering it. The next reader who wants a skip cache
finds the reason it is not here.

# What earns the column instead

A census over 376 live stores, taken 2026-09-01:

| tier | files |
|---|---|
| `symbols` | 75,366 |
| `none` | **24,318** |
| `imports` | 1,304 |

`grammars.capabilities` returns nothing for vue, json and css, so their silence is expected and the
7,587 json files are not a defect. But php, rust, javascript and typescript return the full set --
`calls`, `classes`, `defs`, `imports`, `methods` -- and **6,301 files in those four are silent with
no reason recorded anywhere**. Whether that is a missing grammar, a query that raised, or a file
that genuinely defines nothing is unanswerable from the store, and those three want three different
responses.

# The closed set is five, and it was six

| cause | value |
|---|---|
| the file could not be read | `unreadable` |
| no parser for the language | `no_parser` |
| the language captures nothing | `no_capability` |
| a query raised and was swallowed | `query_failed` |
| parsed clean, nothing to record | `no_symbols` |

The design's sixth, `not_parsed`, is not in the set. `filters.indexable` refuses a path whose
language is empty, so every target reaches the extractor and carries facts, and a value no writer
produces is a filter a reader writes against nothing. `T-299` grades the set against the writers
read from source, which is the mirror of `T-262` over `NODE_KINDS` and for the same reason: a set
and a copy of itself agree about everything.

`query_failed` is the value that pays for the separation. `_run` swallowed a query error and
returned `[]`, byte-identical in the store to a clean parse that found nothing. It is also the one
value that rides beside `tier='symbols'`, where one of two queries matched and the other raised --
so the invariant is one-directional: `none` implies a reason, and a reason does not imply `none`.

# The bar the column had to clear

`producer_version` was dropped from this schema because nothing read it. `store.census` is this
column's reader and `cli.cmd_doctor` prints it beside `gaps`, which is the right neighbour: `gaps`
says a language captures no calls, and `by_reason` says how many files that silence costs.

**If the reader is ever cut, the column is cut with it.** That is the falsifier.

# What it cost

`EXTRACTION_ALGORITHM` 4 to 5, and a rebuild of all 376 stores. `connect()` runs `CREATE TABLE IF
NOT EXISTS`, so an existing store keeps its seven-column `files` and the next write raises `no
column named reason`. The stamp is the only carrier a schema change has, because `incompatible()`
compares `algorithm`, `grammars` and `queries` and never the schema itself.

# What the rebuild read back

All 375 enrolled roots rebuilt in 438 s, 100,997 files parsed, zero errors and zero skips. The
census over the 375 stores that carry the column:

| tier | files | | reason | files |
|---|---|---|---|---|
| `symbols` | 75,364 | | `no_capability` | 17,994 |
| `none` | 24,329 | | `no_symbols` | 6,304 |
| `imports` | 1,304 | | `unreadable` | 31 |

**`count(*) WHERE tier='none' AND reason=''` is 0.** The three reasons sum to 24,329, which is the
`none` count exactly, so every silent file is accounted for and none is accounted for twice.

The 6,301 files this record was written for — php, rust, javascript and typescript, languages with
the full capability set — come back as **6,271 `no_symbols` and 30 `unreadable`, 6,301 exactly**.
That is the answer the census could not give before: they are not a broken parse. They are files
that parsed clean and define nothing, plus 30 the reader could not open. `no_parser` and
`query_failed` are written by no file in the fleet, which is the reading a closed set is for — the
values exist, `T-299` and `T-301` grade them, and the fleet does not currently produce them.

Two stores on disk carry no `reason` column. Both are `tmp*` directories left by a test run, and no
registry row claims either, so the reindex never reached them and `prune` is what removes them.

# What was cut with the cache# What was cut with the cache

A free-form message column: the text is already in `FileFacts.error`, and storing it twice is the
`producer_version` mistake again. Splitting `no_parser` into a missing grammar and an uncached
download: no reader would branch on it. And `tree.root_node.has_error`, which is a real gap -- a
syntactically broken file reports `symbols` off partial matches today -- but recording it would
**change the tier of files that currently answer**, which is a graph change and not a diagnostic.
It needs its own row and its own justification.

[^diff]: {ref: diff}
