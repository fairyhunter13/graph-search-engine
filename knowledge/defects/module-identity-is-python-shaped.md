---
type: Defect
resource: src/graphrag/symtab.py, src/graphrag/resolve.py, src/graphrag/resolvedb.py, src/graphrag/indexwrite.py
title: Module identity is Python-shaped, so a Go or PHP import names nothing
description: "`module_name` spells a module by dotting a file path, and an import row keeps whatever the language wrote. The two spellings agree in Python and Java and in no other language, so `import_edges` writes nothing and a receiver-narrowed call resolves external. 7 of 367 stores hold an IMPORTS edge, and 67.2% of every CALLS edge in the fleet lands on external."
tags: [resolution, imports, go, php, federation, measurement]
status: stable
generated: { by: claude/opus-5, at: 2026-08-30T00:00:00Z }
---

# What was measured

The fleet pass indexed 367 projects, every generation in the fleet included. Two numbers over those
stores:

| Measure | Value |
|---|---|
| IMPORTS edges, whole fleet | 2,435 |
| Stores holding one | 7 of 367 |
| Languages of those 7 | python, java |
| CALLS edges, whole fleet | 2,784,438 |
| CALLS edges whose `evidence` is `external` | 1,872,253, or 67.2% |

The external share per generation:

| Generation | Repository | CALLS | external |
|---|---|---|---|
| Gen-1 | Gen-1 PHP app | 61,613 | 70.0% |
| Gen-2 | Gen-2 PHP app | 65,153 | 75.2% |
| Gen-3 | `gen3-app-c` | 9,427 | 97.3% |
| Gen-3 | Gen-3 PHP app | 5,488 | 94.5% |
| Gen-4 | Gen-4 Go monorepo | 137,205 | 90.0% |

Two concrete answers behind those shares. `neighbors question=importers` on `RateService`
returns an empty list, while more than ten files carry
`use App\Services\V1\Billing\Rates\RateService;`. `neighbors question=callers` on the Go
constructor `NewRate` returns one caller, in the same file, and misses the cross-package
caller at `internal/billing/app/command/add_rate.go:53`.

# Why it happens

`symtab.module_name` spells a module by taking the file path, stripping a build-tool prefix, and
joining the parts with a dot. `symtab.imported_modules` returns whatever the source wrote, unchanged
whenever it has no leading dot. Those two spellings must be equal for an import to name anything.

The extractor reads the real Go file as:

```
Import(module='example.com/acme/app/internal/billing/domain/rates', ...)
```

and names the definition file:

```
internal.billing.domain.rates.rates
```

They differ three ways at once. The import carries a repository prefix the path does not. The import
separates with a slash and the module name with a dot. The import names a **package**, and
`module_name` names a **file**. PHP fails the same way with a backslash and a namespace root. Python
and Java agree by accident of syntax, which is why 7 stores out of 367 hold an IMPORTS edge.

One root cause, two symptoms:

1. `indexwrite.import_edges` looks a resolved import up in `by_module`, misses, and writes no row.
   So `imports` and `importers` answer empty outside Python and Java.
2. `resolve._receiver_modules` narrows the candidate pool to the modules the receiver could name.
   The receiver `rates` matches no module under either spelling, so the set comes back
   empty, `resolve_reference` finds no survivor, and the call is recorded external. A
   package-qualified call therefore never reaches its definition.

The second symptom is the quiet one. An external row is not an error and carries `confidence: 1`,
so a `callers` answer that resolved nothing looks the same as a symbol nothing calls.

# One literal, two meanings, and the split is measurable

`resolve_reference` writes `external=True` at two sites, and both produce the same literal.

| Site | Condition | Meaning |
|---|---|---|
| `resolve.py:131-132` | `table.defines(name)` is empty | the name is defined nowhere here. Honest. |
| `resolve.py:144-145` | the pool was non-empty, then `_receiver_modules` narrowing emptied it | the name **is** defined here and the resolver missed it. |

A reader cannot tell them apart from the answer, but the store can. An external edge whose callee
name also exists as a non-external node is the second site. Measured 2026-08-30:

| Repository | CALLS | external | site 1, honest | site 2, miss |
|---|---|---|---|---|
| Gen-4 Go monorepo (go) | 137,205 | 123,520 (90.0%) | 77,342 (62.6%) | 46,178 (37.4%) |
| TypeScript app (typescript) | 31,109 | 25,705 (82.6%) | 21,205 (82.5%) | 4,500 (17.5%) |

So 62.6% is the floor the Go monorepo can reach on this resolver, and the 37.4% above it is the prize. The
Go prize is more than double the TypeScript one, because TypeScript's own `import` rows already
carry a relative path that sometimes matches.

# `same_class` never fires for Go

The Go monorepo histogram carries no `same_class` row at all: `external` 123,520, `same_file` 7,439,
`package` 5,858, `global` 388, and no `import` row either. `_enclosing_class` finds the class a
call sits lexically inside, and a Go method sits beside its type rather than inside it. So the
0.95 tier is unreachable in Go by construction, and not by a missing query.

# What the capability table says, and what it is worth

`grammars.py` advertises `imports` for php, go and javascript, and the report is honest at the level
it measures: an import **query** exists for those grammars, and it does extract rows. The rows then
fail to match a module name. So a capability answer is a statement about extraction and never about
resolution, and no `gaps` entry reports the difference.

# What this does not change

The graph still answers the questions that do not cross a module boundary. `find_symbol` is exact.
`DEFINES` and `CONTAINS` are structural and complete. `IMPLEMENTS` resolved 36,646 edges. A
same-file or same-class caller resolves at 0.90 and 0.95, and the `NewRate` case was read
against the source and confirmed correct.

The workflow is unharmed where the caller reads `evidence` first, which is the standing rule.
It is harmed where a reader takes an empty `callers` list as proof that nothing calls a symbol.

# Not fixed here

The fix is a per-language module identity: a Go module named for its directory and stripped of the
`module` line's prefix, and a PHP module named by its namespace rather than its path. That is
resolver work over four languages, and it was not in the scope that indexed the fleet. It is
recorded and not bought.

For Go and TypeScript the SCIP overlay closes part of the same slice without that work, because a
real compiler resolves what a syntactic receiver cannot. It was turned on and measured on
2026-08-30, and every figure in this concept above is the reading before it:

| Repository | `external` before | `external` after | `evidence: scip` |
|---|---|---|---|
| Gen-4 Go monorepo (go) | 123,520 (90.0%) | 109,065 (79.5%) | 26,747 (19.5%) |
| TypeScript app (typescript) | 25,705 (82.6%) | 24,387 (79.0%) | 4,397 (14.2%) |

Neither crossed its honest floor, which is the check that SCIP invented no edge. Go took about a
third of its own 37.4% miss and TypeScript about 29% of its 17.5%, so the defect is reduced and not
gone. Reaching the tier at all needed a second fix, in
[a project is not one build](a-project-is-not-one-build.md). `projcfg.effective` now inherits `scip` and
`scip_indexers` to a federated member, which is the only way the tier can reach a repository
nobody here owns. PHP keeps the defect whole: `scip-php` has no invocable command, so Gen-1,
Gen-2 and Gen-3 stay at the measured shares above.

# The fix, and the defect inside the fix

`D-40` gave `module_name` and `resolve_module` a spelling per language: `package` for Go, named by
its directory with the `go.mod` prefix dropped; `namespace` for PHP, named by its PSR-4 namespace;
`relative` for TypeScript and JavaScript, named by the path a `./x` specifier resolves to; and the
dotted form Python and Java already had. Python and Java outputs are byte-identical.

Each name carries its spelling as a prefix — `package:internal/billing/rates`, not
`internal/billing/rates`. That tag is not decoration. Untagged, `Orders.php` and `orders.ts` in one
directory are one path with two suffixes, so they became one module and each file answered for the
other's `Order`. The two-engine receipt read it as distinctive precision falling from 1.000 to
0.980, which is the only reason the collision was found at all.

Then the tag broke the thing it was added to fix. Two sites read a module's last segment by
splitting it on a dot — `resolve._receiver_modules` and `resolvedb.receiver_modules`, the index-time
and query-time halves of the same rule. `rsplit(".", 1)[-1]` over `package:internal/billing/rates`
returns the whole string, so a Go receiver matched no module, the narrowed pool came back empty,
and `resolve_reference` wrote `external=True`. Every member call on an imported Go package resolved
external — worse than the defect this concept records, and invisible to the two-engine receipt,
whose corpus is Python and TypeScript and holds no Go at all.

`symtab.receiver_names` and `symtab.submodule` ask the spelling for its own separator instead of
assuming a dot. `receiver_names` folds case for `namespace` alone, because `module_name` lowercases
PSR-4 to settle `App\` sitting under `app/`, and a PHP receiver is written in the class's own case.

Measured against the predecessor, `rates.Convert(1)` from a Go file importing that package:

| Engine | Result |
|---|---|
| Before the fix | `external: True`, no candidates |
| After | one candidate, the defining file, `evidence: import` |

`T-297` and `T-298` hold the Go and PHP halves, and both fail on the predecessor.

Neither half needed a reindex, and that was measured rather than argued. `resolve_file_local` runs
at index time, so both engines were run over a 2,461-file Go repository whole and 3,000 files each
of a 12,697-file PHP application and a 5,156-file TypeScript service, diffing the exact
`(line, name, receiver)` signature of every decided and deferred reference. Zero of 8,460 files
differ, and a synthetic positive control proves the harness catches a flip when one exists. The
guard the tag reaches can only override an already non-empty same-file pool, which needs a file to
import its own module — a compile error in Go.

The one index-time string that does change is the module node's `name`, written verbatim by
`indexwrite.write_nodes`. It is a label: `dbread._POOL` matches names under `n.kind != 'module'`
and `dbread.module_node` selects by `file_id`. No join reads it, so `EXTRACTION_ALGORITHM` stays
at 4.

The lesson is the one this whole concept is about, arriving a second time. A name is only a name
inside a spelling, and code that reads a name apart from its spelling is guessing. The first round
guessed that every module was dotted. The second guessed that every module name split on a dot.

Related: [prune wiped the graph but kept the directory](prune-wiped-the-graph-but-kept-the-directory.md),
[the daemon never saw a row another process wrote](the-daemon-never-saw-a-row-another-process-wrote.md).
