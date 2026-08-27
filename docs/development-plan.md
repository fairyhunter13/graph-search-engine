# Development plan — graphrag

```
IDs      D-nn development task. Append-only.
Status   planned | in-progress | done | blocked | dropped
         blocked carries the observed behaviour. dropped carries one line of reason.
Columns  | ID | Title | Status | Paths it owns | T-nn covering it |
```

The test plan is `test-plan.md` beside this file. It owns every `T-nn` named here.

# Context

This repo is a code graph search engine on tree-sitter. It parses source, extracts symbols and
builds edges. It answers the structural questions that neither grep nor semantic retrieval reaches.
Those questions are: who calls this, what breaks if I change it, what implements this interface.

The semantic sibling is `coderag` in `rag-search-engine`. Same architecture, same conventions, a
different question. Nothing is imported from it.

`coderag` dropped a `graph` tool and about 4200 lines of symbol extraction. It recorded the drop so
that nobody would re-propose it. That record is honoured here, not overturned. A graph capability
does not belong inside a retrieval engine, so it gets its own store, daemon and tools.

The project ends when a session in any profile reaches this engine without being told to, and gets
an edge rather than a ranked guess.

# Decisions

Each row states the choice. A settled decision graduates to `knowledge/decisions/` and is then
cited here in one line rather than repeated.

| Axis | Choice |
|---|---|
| Host language | Python 3.12+, `uv`, `hatchling`, src layout |
| Graph store | SQLite, one file per project, recursive CTE traversal |
| Deployment | Own package, own daemon, own MCP server |
| Embeddings | None. No GPU, no model. FTS5 over symbol names only |
| Resolution | Two-phase, import-scoped, confidence-ranked |
| No `tags.scm` | Parse, file and import edges only. No fabricated symbols |
| Capability model | A set per language, not a tier. Reported with every answer |
| Import queries | Hand-written for all 68 `tags.scm` languages |
| Grammar source | The pack, pinned exactly. Parsers cached, first run needs network |
| SCIP | Optional overlay, off by default, upgrades resolution only |
| SCIP bindings | Generated from `scip.proto` at tag `v0.9.0`, vendored |
| SCIP trust | Per-indexer capability table. Exit 0 proves nothing |

Rejected on evidence. Stack graphs cover 4 languages at about 6000 lines of DSL each, and the
project was archived in September 2025. Hand-written type inference reimplements a language server,
permanently. A regex identifier fallback for gap languages gives bag-of-words precision, and a graph
query would read that as fact.

# Architecture

One process per user, serving every enrolled project. A per-project daemon would multiply the write
queue by the project count, and lose the single-writer invariant that keeps the store correct.

The shape is copied from `coderag`, and the code is not.

- Flat package, no subpackages. Every module under 300 lines, enforced by a test.
- `config.py` imports no sibling, so a cycle is unresolvable.
- Module as interface. No ABCs, no protocols, no registry of classes, no DI container.
- Dataclass contracts between stages, each `@dataclass(slots=True)`.
- Versioned rebuild, never `ALTER`. A `meta` table stamps grammar versions and query hashes.
- Content-hash diff is the whole of staleness. The question is whether the store matches the disk.
- One queue, one worker. The queue is the write serializer.
- JSONL ledgers, best-effort, never read back as state. A `trace_id` rides in every error.

The one deviation from `coderag`. Its `config_signature` reconcile gate is not copied, because here
a signature change means a grammar pin moved, and `meta.incompatible(conn)` already owns that.

# Components

`src/graphrag/`, flat, about 25 modules.

| Module | Role | Invariant it owns |
|---|---|---|
| `config.py` | constants, env switches, paths | imports no sibling |
| `filters.py` | extension map, denylists | one `indexable()` for watcher and indexer |
| `projcfg.py` | strict `.graphrag.yaml` parse | an unknown key is an error |
| `entry.py` | `ProjectEntry` and its JSON shape | one row, one resolved path |
| `registry.py` | `projects.json` under `flock` | `_mutate` loads inside the lock |
| `discover.py` | enumeration, `FileMeta`, hash diff | paths resolve before ownership |
| `grammars.py` | pack access, capability set | capability is per capture |
| `queries.py` | tags cache, import queries | every capture name is mapped or ignored |
| `queries/tags_extra/` | a repair query per measured gap | the pin stays exact and the pack unforked |
| `extract.py` | per-file parse to dataclasses | writes nothing global |
| `symtab.py` | phase-two global symbol table | built after every file is in |
| `resolve.py` | candidate scoring, confidence | never forces a single edge |
| `store.py` | schema, nodes, edges, FTS5 | both tables touched on every delete |
| `indexwrite.py` | batched write loop | one writer |
| `index.py` | job queue, worker, one pass | a running job is re-queued |
| `traverse.py` | recursive CTE, cycle detection | terminates, never double-counts |
| `query.py` | the surface behind the tools | defaults to `resolved = 1` |
| `scip/` | the optional overlay | never owns extraction |
| `scope.py` | workspace pin | one root per session |
| `federation.py` | member discovery | expands one level, not transitively |
| `peers.py` | peer identity | identity is stable across restarts |
| `tools.py` | the four MCP tools | an unknown argument names the valid set |
| `server.py` | the daemon | exits with `os._exit(0)` |
| `bridge.py` | stdio bridge | one request, one response |
| `cli.py` | the operator surface | everything that is not a tool |
| `watch.py` | debounced observer | re-arms conditionally |
| `progress.py` | a file per project | polled, never a protocol notification |
| `health.py` | per-identity state | pages on two consecutive failures |
| `ledger.py` | append-only JSONL | never read back as state |
| `trace.py` | trace ids | echoed in every error |
| `systemd.py` | per-user units | written and enabled by the CLI |

# Structure

```
src/graphrag/*.py            flat, one package
src/graphrag/scip/           the only subpackage, deletable in one move
src/graphrag/queries/imports/<lang>.scm
tests/                       real fixtures, no mocks
docs/                        this pair
knowledge/                   OKF v0.2, fleet profile
```

The rule that keeps it true. A module over 300 lines fails a test, and a new subpackage needs the
argument `scip/` makes: optional, isolable, deletable in one move.

# Endpoints

Four MCP tools, because a graph answers four shapes of question. Everything else is the CLI,
because everything else is an operator job.

| Tool | Inputs | Output | Error contract |
|---|---|---|---|
| `index` | `root` | enrolment status | an unindexable root is named |
| `find_symbol` | `name`, `lang`, `kind` | locations, never bodies | unknown `lang` names the valid set |
| `neighbors` | `symbol`, `direction`, `kind` | one hop, with confidence | a missing capability is reported |
| `blast_radius` | `symbol`, `depth` | transitive dependents | a depth over the ceiling is refused |

Every tool defaults to `resolved = 1`, and reports `candidate_count` when it opens up. Results
carry `confidence` and `evidence`, so a caller can tell a fact from a guess.

The CLI carries `index`, `doctor`, `status`, `forget`, `prune`, `serve` and the systemd unit
writers. `graphrag doctor` prints the per-language capability table for the whole project.

# Integration

The engine is finished when a session reaches it unprompted. Three pieces meet.

The daemon listens on `127.0.0.1:8766` and holds every enrolled project. `ccw` registers the URL in
all five profiles through `policy.RequiredMCPServers`. A `graphrag-reach` SessionStart hook posts
the session root to `/register`, so opening a session in a repo is what enrols it.

The routing rule is doctrine, and it is a pipeline rather than a choice. `coderag` ranks by meaning
and turns a vague question into a symbol name. `graphrag` turns that name into edges. The order
never reverses, because a graph query needs a name to start from.

The command that proves it end to end. Index this repo, run `graphrag doctor`, then ask `neighbors`
for the callers of a known function and check them by hand.

# Task table

| ID | Title | Status | Paths it owns | T-nn covering it |
|---|---|---|---|---|
| D-01 | The floor: config, store, discovery | done | src/graphrag/config.py, src/graphrag/filters.py, src/graphrag/store.py, src/graphrag/discover.py, src/graphrag/entry.py, src/graphrag/registry.py, src/graphrag/projcfg.py | T-01, T-02 |
| D-02 | Grammars, queries, extraction, wave one | done | src/graphrag/grammars.py, src/graphrag/queries.py, src/graphrag/extract.py, src/graphrag/queries/imports, src/graphrag/queries/tags_extra, tests/fixtures/wave1 | T-03, T-04, T-05, T-06, T-33, T-34, T-35 |
| D-03 | Symbol table and ranked resolution | done | src/graphrag/symtab.py, src/graphrag/resolve.py | T-07, T-08, T-36, T-37 |
| D-04 | Index loop, traversal, query surface | planned | src/graphrag/index.py, src/graphrag/indexwrite.py, src/graphrag/traverse.py, src/graphrag/query.py | T-09, T-10 |
| D-05 | Import queries, the remaining waves | planned | src/graphrag/queries/imports | T-11 |
| D-06 | MCP tools, daemon, CLI, stdio bridge | planned | src/graphrag/tools.py, src/graphrag/server.py, src/graphrag/cli.py, src/graphrag/bridge.py | T-12, T-13, T-14, T-15 |
| D-07 | Watcher, health, progress, ledgers | planned | src/graphrag/watch.py, src/graphrag/health.py, src/graphrag/progress.py, src/graphrag/ledger.py, src/graphrag/trace.py | T-16, T-17 |
| D-08 | SCIP overlay behind the coverage guard | planned | (deferred, no code this pass) | T-18, T-19 |
| D-09 | Fleet registration across five profiles | planned | (ccw) internal/policy/shared.go | T-20, T-21 |
| D-10 | Two-engine gate and the routing rule | planned | (ccw) internal/hooks/treesearch.go | T-22, T-23, T-24, T-25 |
| D-11 | systemd units and reach enrolment | planned | src/graphrag/systemd.py | T-26, T-27 |
| D-12 | The OKF profile record and bundle root | done | knowledge/index.md, knowledge/log.md, knowledge/policies, tests/test_bundle.py | T-28, T-38, T-39, T-40 |
| D-13 | The first working attester | done | knowledge/attesters, knowledge/computations, knowledge/skills, tests/test_attester.py | T-29, T-30, T-41, T-42, T-43, T-44 |
| D-14 | Gate lines and the attester contract check | planned | .githooks/pre-push | T-31, T-32 |

`D-09` and `D-10` own paths in a different repository, so their rows carry the `(ccw)` prefix and
the path-anchor check skips them. `git ls-files` here cannot see them. That is a real limit of the
gate, and it is written down rather than worked around.

`D-03` carries the load-bearing claim of the whole project. `T-07` measures it on CPython
`v3.12.7`, 755 files of `Lib` with the test tree excluded, 53853 call sites. Global name matching
gives 10.86 candidate files per site and 54.5% of sites are ambiguous. Import scoping gives 1.49
and 17.7%. That is a collapse of 7.3 times.

The case asserts the ratio and a wide band, not the two numbers. A corpus at another tag moves both
arms together, so an exact equality would fail on a bump that changed nothing. What is not allowed
to move is the ratio. If it drops below 6, the design premise is gone. `D-03` then goes `blocked`
with the observed numbers, and the design is not quietly relaxed.

`D-08` is deferred by decision. The row stays `planned` and no code lands this pass.

## The language waves

Answered 2026-08-27, against a census of the operator's own repositories rather than a guess. The
counts are tracked files by extension across every clone under `~/git`.

```
wave 1  php, javascript, typescript, tsx, python      D-02
wave 2  java, go, rust, swift                         D-05
wave 3  kotlin, scala, ruby, c, cpp, csharp           D-05
wave 4  the remaining tags.scm languages              D-05
```

`php` leads on 35657 files, ahead of `js` at 31024 and `ts` at 21816. It also carries a full
capability set: calls, implementations and four definition kinds. `python` holds 843 files and rides
in wave 1 for one reason only, that `T-07` measures against a Python corpus.

Two of the operator's languages have no `tags.scm` at all. `groovy` holds 2222 files and `vue` holds
1163, and both answer no symbol question from tree-sitter. That is reported as a gap, per the
experience bar, and it is not a defect to fix.

`T-07` measures against a CPython clone pinned to a tag, fetched once into a cache directory. The
case is marked `corpus` and skips when the clone is absent. The local `/usr/lib/python3.12` was
rejected as the corpus: a distro update moves the number, and no other machine reproduces it. The
receipt carries the corpus tag, so the attester compares like with like.
