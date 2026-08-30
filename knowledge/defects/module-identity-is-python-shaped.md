---
type: Defect
resource: src/graphrag/symtab.py, src/graphrag/resolve.py, src/graphrag/indexwrite.py
title: Module identity is Python-shaped, so a Go or PHP import names nothing
description: "`module_name` spells a module by dotting a file path, and an import row keeps whatever the language wrote. The two spellings agree in Python and Java and in no other language, so `import_edges` writes nothing and a receiver-narrowed call resolves external. 7 of 367 stores hold an IMPORTS edge, and 67.2% of every CALLS edge in the fleet lands on external."
tags: [resolution, imports, go, php, federation, measurement]
status: stable
generated: { by: claude/opus-5, at: 2026-08-30T00:00:00Z }
---

# What was measured

The fleet pass indexed 367 projects, every Acme generation included. Two numbers over those
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
| Gen-1 | `gen1-php-app` | 61,613 | 70.0% |
| Gen-2 | `gen2-php-app` | 65,153 | 75.2% |
| Gen-3 | `gen3-app-c` | 9,427 | 97.3% |
| Gen-3 | `gen2-erp/miti` | 5,488 | 94.5% |
| Gen-4 | `go-monorepo` | 137,205 | 90.0% |

Two concrete answers behind those shares. `neighbors question=importers` on `RateService`
returns an empty list, while more than ten files carry
`use App\Services\V1\Projects\Commitment\RateService;`. `neighbors question=callers` on the Go
constructor `NewRate` returns one caller, in the same file, and misses the cross-package
caller at `internal/billing/app/command/add_rate.go:53`.

# Why it happens

`symtab.module_name` spells a module by taking the file path, stripping a build-tool prefix, and
joining the parts with a dot. `symtab.imported_modules` returns whatever the source wrote, unchanged
whenever it has no leading dot. Those two spellings must be equal for an import to name anything.

The extractor reads the real Go file as:

```
Import(module='github.com/acme/cx/internal/billing/domain/rates', ...)
```

and names the definition file:

```
internal.billing.domain.rates.rate
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

Related: [prune wiped the graph but kept the directory](prune-wiped-the-graph-but-kept-the-directory.md),
[the daemon never saw a row another process wrote](the-daemon-never-saw-a-row-another-process-wrote.md).
