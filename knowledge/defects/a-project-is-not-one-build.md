---
type: Defect
resource: src/graphrag/scip/run.py, src/graphrag/scip/__init__.py, src/graphrag/scip/ingest.py
title: A project is not one build, so the overlay indexed one module of eight
description: "`overlay` invoked each indexer once, at the project root. An indexer resolves the build it stands in and no other, so on the Go monorepo scip-go saw 2 of 2012 Go files, covered 0% and was correctly refused. The tier was unreachable for every multi-module repository, and the refusal named the coverage floor rather than the cause."
tags: [scip, overlay, go, typescript, monorepo, coverage]
status: stable
generated: { by: claude/opus-5, at: 2026-08-30T00:00:00Z }
---

# What was measured

The Go monorepo was indexed with `scip: true` and `scip_indexers: [scip-go, scip-typescript]`. The pass ran
in 12.8 s, read 2,425 files, and moved no CALLS edge at all. `overlay` reported:

```
scip-go: refused: scip-go covers 2 of 2012 files (0%), under the 60% floor
```

The build is clean and the guard is right. `find . -name go.mod` returns **8 files**, and
`go list ./...` at the root returns **1 package**. 2,010 of the 2,012 Go files live under
`internal/`, in seven sibling modules the root module does not contain. The TypeScript app is the same
shape: **8 `tsconfig.json` files and none at the root**.

Run by hand inside one of them, the tool works and the prize is large:

```
cd internal/billing && scip-go index
Visiting Packages [71/71]
Indexing Implementations [2264/2264]
real 0m5.190s
```

# Why it happens

An indexer is a compiler front end. It resolves the one build whose manifest it stands beside, and
a sibling module is another build. `overlay` modelled a project as one build, which is true for a
single-module repository and false for every monorepo. So the coverage guard did its job on an
index that was correct for the module it described, and the message named the floor rather than the
reason the index was small.

The floor made the failure quiet. 0% is under 60%, so nothing was written and nothing was lost. An
operator reading that line would go looking for a broken Go build.

# The fix

A project is a list of build units, and the fix is in three places at once.

1. `run.Indexer` carries a `unit` marker: `go.mod` for scip-go, `tsconfig.json` for
   scip-typescript. Empty means one invocation covers the project, which is what every other
   indexer keeps.
2. `run.units` lists every directory holding that marker, skipping `vendor`, `node_modules`,
   `testdata` and any dotted directory. Those hold another project's modules, and indexing them
   attributes their files here.
3. `overlay` invokes the indexer once per unit, and a unit that refuses costs the others nothing.

The second half is what makes the first half work. An index written inside a sub-module names its
documents relative to that module, so `ingest` and `coverage` take the unit's prefix and re-base
each document onto the path the store holds. They also take the units nested below, because a unit
prefix contains every deeper unit's files as well. Without that the root module would still be
graded against all 2,012 files and still refuse.

No floor moved. Each unit is graded separately against tree-sitter's own census for that unit.

# What it bought

The Go monorepo, all eight units, 38.9 s wall:

| | before | after |
|---|---|---|
| CALLS `external` | 123,520 (90.0%) | 109,065 (79.5%) |
| CALLS `evidence: scip` | 0 | 26,747 (19.5%) |
| IMPLEMENTS edges | 0 | 31 |
| nodes | 33,899 | 33,899 |

The 62.6% honest floor was not crossed, which is the check that SCIP invented no edge. 32 CALLS
rows collapsed as duplicates on upsert, and IMPLEMENTS gained 31, so the edge total moved by −1 and
nothing was destroyed.

The concrete miss recorded in
[module identity is Python-shaped](module-identity-is-python-shaped.md) is closed. `NewRate`
returned one same-file caller and missed the cross-package one at
`internal/billing/app/command/add_rate.go`. It now returns eight callers, every one
`evidence: "scip"`, that caller among them.

Related: [the overlay doubled its own edges](the-overlay-doubled-its-own-edges.md),
[scip-python drops cross-package references and exits 0](scip-python-drops-references-and-exits-zero.md).
