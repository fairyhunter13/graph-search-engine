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
| Import queries | Hand-written for 32 of the 68 `tags.scm` languages. The other 36 are a reported gap |
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
| `federation.py` | member discovery | walks the symlinks, expands one level, not transitively |
| `peers.py` | peer identity | identity is stable across restarts |
| `tools.py` | the four MCP tools | an unknown argument names the valid set |
| `server.py` | the daemon | exits with `os._exit(0)` |
| `bridge.py` | stdio bridge | one request, one response |
| `cli.py` | the operator surface | everything that is not a tool |
| `watch.py` | debounced observer | re-arms on a moved registry stamp |
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
| D-01 | The floor: config, store, discovery | done | src/graphrag/config.py, src/graphrag/filters.py, src/graphrag/store.py, src/graphrag/discover.py, src/graphrag/entry.py, src/graphrag/registry.py, src/graphrag/projcfg.py, tests/test_store.py, tests/test_registry.py, tests/test_discover.py, tests/test_projcfg.py, tests/test_hygiene.py | T-01, T-02, T-94..T-101, T-122 |
| D-02 | Grammars, queries, extraction, wave one | done | src/graphrag/grammars.py, src/graphrag/queries.py, src/graphrag/extract.py, src/graphrag/queries/imports, src/graphrag/queries/tags_extra, tests/fixtures/wave1, tests/test_extract.py, tests/test_queries.py, tests/test_grammars.py | T-03, T-04, T-05, T-06, T-33, T-34, T-35, T-60 |
| D-03 | Symbol table and ranked resolution | done | src/graphrag/symtab.py, src/graphrag/resolve.py, tests/test_resolve.py | T-07, T-08, T-36, T-37 |
| D-04 | Index loop, traversal, query surface | done | src/graphrag/index.py, src/graphrag/indexwrite.py, src/graphrag/traverse.py, src/graphrag/query.py, tests/test_index.py, tests/test_perf.py | T-09, T-10, T-45..T-55 |
| D-05 | Import queries, the remaining waves | done | src/graphrag/queries/imports, tests/test_import_queries.py | T-11, T-56, T-57, T-58 |
| D-06 | MCP tools, daemon, CLI, stdio bridge | done | src/graphrag/tools.py, src/graphrag/server.py, src/graphrag/cli.py, src/graphrag/bridge.py, tests/test_tools.py, tests/test_server.py | T-12, T-13, T-14, T-15, T-21, T-61, T-62, T-63, T-64 |
| D-07 | Watcher, health, progress, ledgers | done | src/graphrag/watch.py, src/graphrag/health.py, src/graphrag/progress.py, src/graphrag/ledger.py, src/graphrag/trace.py, tests/test_watch.py, tests/test_health.py | T-16, T-17, T-66..T-76 |
| D-08 | SCIP overlay behind the coverage guard | done | src/graphrag/scip/, src/graphrag/config.py, src/graphrag/index.py, tests/scipwrite.py, tests/fixtures/scip/scip.proto, tests/test_scip_wire.py, tests/test_scip_read.py, tests/test_scip_offsets.py, tests/test_scip_symbol.py, tests/test_scip_guard.py, tests/test_scip_ingest.py, tests/test_scip_run.py | T-18, T-19, T-102..T-110, T-121 |
| D-09 | Fleet registration across five profiles | done | (ccw) internal/policy/shared.go | T-20, T-21 |
| D-10 | Two-engine gate and the routing rule | done | (ccw) internal/hooks/treesearch.go | T-22, T-23, T-24, T-25 |
| D-11 | systemd units and reach enrolment | done | src/graphrag/systemd.py, src/graphrag/reach.py, tests/test_systemd.py, (ccw) internal/hooks/graphragreach.go | T-26, T-27, T-85..T-89, T-117, T-118, T-119, T-120 |
| D-12 | The OKF profile record and bundle root | done | knowledge/index.md, knowledge/log.md, knowledge/policies, tests/test_bundle.py | T-28, T-38, T-39, T-40, T-126 |
| D-13 | The first working attester | done | knowledge/attesters, knowledge/computations, knowledge/skills, tests/test_attester.py | T-29, T-30, T-41, T-42, T-43, T-44 |
| D-14 | Gate lines and the attester contract check | done | .githooks/pre-push, scripts/check_attester_contract.py, knowledge/constraints, knowledge/decisions | T-31, T-32 |
| D-15 | Source roots, so a dotted import matches a path | done | src/graphrag/symtab.py, tests/test_resolve.py | T-59 |
| D-16 | Workspace scope, federation and peer identity | done | src/graphrag/scope.py, src/graphrag/federation.py, src/graphrag/peers.py, tests/test_federation.py | T-65, T-77..T-84 |
| D-17 | The registry row carries the reach figures | done | src/graphrag/entry.py, src/graphrag/registry.py, src/graphrag/index.py, src/graphrag/cli.py | T-90 |
| D-18 | The caller question, graded against both engines | done | scripts/two_engine_measure.py, tests/test_two_engine.py | T-91, T-92 |
| D-19 | Capture the receiver, so a member call resolves to its own module | done | src/graphrag/extract.py, src/graphrag/resolve.py | T-93 |
| D-20 | Continuous integration, the gate a skipped hook still meets | done | .github/workflows/ci.yml, tests/test_ci.py | T-112..T-115 |
| D-21 | The receipt is an artifact of the run, never a literal | done | src/graphrag/config.py, tests/test_resolve.py, tests/test_attester.py, scripts/two_engine_measure.py | T-111, T-123 |
| D-22 | The re-export pass, so a name resolves through the package initialiser | planned | src/graphrag/symtab.py, src/graphrag/resolve.py, tests/test_resolve.py | T-116 |
| D-23 | Ambiguity is the candidate count, and the count reaches the caller | done | src/graphrag/traverse.py, src/graphrag/query.py, src/graphrag/tools.py, src/graphrag/store.py, tests/test_tools.py | T-124 |
| D-24 | The overlay replaces its own edges, so a re-ingest is idempotent | done | src/graphrag/scip/ingest.py, tests/test_scip_ingest.py | T-125 |
| D-25 | An import query for each of the 36 remaining `tags.scm` languages | dropped | src/graphrag/queries/imports | T-11 |
| D-26 | The headless probe, so a selection claim is an artifact of the run | done | scripts/headless_probe.py, tests/test_probe.py | T-127, T-128 |
| D-27 | An expression receiver names no module, so the call leaves the repo | done | src/graphrag/resolve.py, src/graphrag/config.py, tests/test_resolve.py, tests/test_two_engine.py | T-208 |
| D-28 | One frontmatter reader, and the trust tier section 5.3 names | done | scripts/okf_frontmatter.py, tests/test_bundle.py | T-192, T-194, T-195 |
| D-29 | Every index gloss is checked against its concept description | done | scripts/check_index_gloss.py, .githooks/pre-push, tests/test_bundle.py | T-193 |
| D-30 | The bundle records what it cannot cite, and the shrink-gate deviation | done | knowledge/references, knowledge/decisions, tests/test_attester.py | T-209 |
| D-31 | A corrected citation is not a dropped source, and the private URL goes | done | scripts/check_no_shrink.py, knowledge/decisions, tests/test_bundle.py | T-210 |
| D-32 | The quiet window, so a burst of saves buys one pass and not one each | done | src/graphrag/config.py, src/graphrag/index.py, src/graphrag/watch.py, src/graphrag/extract.py, tests/test_watch.py | T-16, T-214, T-215 |
| D-33 | A receipt carries whether its own run can be read off | done | src/graphrag/config.py, knowledge/attesters, scripts/two_engine_measure.py, tests/test_attester.py, tests/test_two_engine.py, tests/test_resolve.py, scripts/check_attester_contract.py | T-211, T-212, T-213, T-216, T-217 |
| D-34 | Prune removes the store directory, so the orphan count reaches zero | done | src/graphrag/cli.py, src/graphrag/registry.py, tests/test_registry.py | T-218 |
| D-35 | Members are discovered by walking the symlinks, and `federation_exclude` bounds the walk | done | src/graphrag/federation.py, src/graphrag/projcfg.py, src/graphrag/filters.py, tests/test_discovery.py | T-219..T-225 |
| D-36 | `exclude` and `languages` reach the index pass, which read neither | done | src/graphrag/discover.py, src/graphrag/index.py, tests/test_discovery.py | T-228..T-231 |
| D-37 | A deleted project loses its row on the filesystem event, behind a parent test and a grace period | done | src/graphrag/prune.py, src/graphrag/watch.py, tests/test_prune.py | T-232..T-238 |
| D-38 | `find_symbol` spans the federation and names the project holding each hit | done | src/graphrag/tools.py, tests/test_discovery.py | T-239, T-240 |
| D-39 | Every writer of the registry re-arms the watcher, including one in another process | done | src/graphrag/watch.py, src/graphrag/tools.py, tests/test_watch.py | T-241, T-242 |
| D-40 | A module identity per language, so a Go or PHP import names the file it imports | planned | src/graphrag/symtab.py, src/graphrag/resolve.py, src/graphrag/indexwrite.py | |
| D-41 | A dead row takes its graph with it, quarantined for a week and behind an idle floor | done | src/graphrag/prune.py, src/graphrag/quarantine.py, src/graphrag/registry.py, src/graphrag/cli.py | T-243..T-247 |
| D-42 | The watcher survives a re-arm in the same pass as a deletion, and an error mid-arm | done | src/graphrag/watch.py, tests/test_watch.py | T-248, T-249 |
| D-43 | A row whose directory is gone is reported, and an unmounted volume is never read as a deletion | done | src/graphrag/prune.py, src/graphrag/entry.py, src/graphrag/registry.py, src/graphrag/cli.py | T-250 |
| D-44 | An index pass returns its freed pages to the filesystem | done | src/graphrag/store.py, src/graphrag/index.py, src/graphrag/cli.py | T-251 |

`D-09` and `D-10` own paths in a different repository, so their rows carry the `(ccw)` prefix and
the path-anchor check skips them. `git ls-files` here cannot see them. That is a real limit of the
gate, and it is written down rather than worked around.

`D-03` carries the load-bearing claim of the whole project. `T-07` measures it on CPython
`v3.12.7`, 755 files of `Lib` with the test tree excluded, 53853 call sites. Global name matching
gives 10.86 candidate files per site and 54.5% of sites are ambiguous. Import scoping gives 1.19
and 7.2%. That is a collapse of 9.1 times.

The case asserts the ratio and a wide band, not the two numbers. A corpus at another tag moves both
arms together, so an exact equality would fail on a bump that changed nothing. What is not allowed
to move is the ratio. If it drops below 6, the design premise is gone. `D-03` then goes `blocked`
with the observed numbers, and the design is not quietly relaxed.

`D-08` was deferred by answer and then asked for by name, so the row moved from `planned` to
`done` in one pass. Two things in it deviate from part A and each has a `knowledge/decisions/`
record. The reader is a stdlib protobuf decoder and not a vendored `scip_pb2.py`, because the plan
already required a hand-written walk at `Document` granularity and gencode would add a second pin
for a tier that is off by default. And the `GRAPHRAG_SCIP_ENABLED` switch defaults on, because the
project's own `.graphrag.yaml` is the opt-in and a second switch defaulting off made the first one
unreachable.

The tier ships with the coverage guard from day one, and `T-19` is the case that proves the guard
refuses before it writes. Exit status proves nothing here: `scip-python` retries a failed analysis
100 times, drops the file, writes the index and exits 0.

`D-24` gives the `producer` column its first reader. Part A asked for three columns on every edge
row: `producer`, `producer_version` and the source commit SHA. Their stated purpose was a scoped
delete plus insert per language. Only the delete is load-bearing, and it keys on the producer alone.

So `producer_version` and the commit SHA are **dropped**. Neither has a reader. A pin move rebuilds
the whole store through `store.incompatible`, and a re-ingest of one index replaces that producer's
rows whatever version wrote them. Two columns nothing queries are two columns to keep true.

`D-25` is the reason `D-05` is `done` at 32 languages. The design asked for an import query for all
68, and wave 4 is the half that never landed. It is `dropped` and not `planned`, because the census
that set the waves put every remaining language under 300 tracked files here. A gap the capability
report names costs a caller less than a query nobody grades. A row is added the day one of those
languages carries real work.

`D-05` ends with 32 of the 68 `tags.scm` languages carrying an import query. `scala` is a declared
gap and not an oversight. Its grammar spells `import a.b.c` as three sibling `path:` fields, and the
extractor reads the first capture, so any pattern returns one segment or garbage. A wrong module
name scopes resolution to the wrong file, which is worse than the repo-global fallback the gap
already prints.

`D-15` is the second thing `D-05` revealed. For java, kotlin, scala and go an import names
`com.acme.Foo`, while `symtab.module_name` derives `src.main.java.com.acme.Foo` from the path. The
two never match, so import scoping does no work on those languages and every reference falls back to
repo-global. The fix is a source-root prefix stripped before the module name is formed, and it is
its own row rather than silent scope inside `D-05`.

A vendored query with one node type the grammar does not carry fails to compile whole, and
`extract._run` returns no matches rather than raising. The file then reads as a language with no
import syntax. `sourcepawn` shipped that way inside this row, on a `string_content` child that
grammar has no name for. `T-56` compiles every vendored query against its own grammar, which is the
only check that sees it.

`D-04` carries the throughput floor, and the floor moved. The design quoted 334 files per second
from an upstream figure that timed a parse plus a tags query. This engine also runs capture
normalization, scope attribution and the import query, so the two count different work. Measured
2026-08-27 on the same 755 files, single core, three runs: 303.7, 307.2 and 306.6 files per second
and 5.0 MB per second. An earlier run the same day read 117.8, and that build compiled a fresh
`ts.Query` for every file. `T-10` therefore sets its floor at 200, which is 34 percent under the
measurement. It is a regression detector, and the margin absorbs a loaded machine.

## The language waves

Answered 2026-08-27, against a census of the operator's own repositories rather than a guess. The
counts are tracked files by extension across every clone under `~/git`.

```
wave 1  php, javascript, typescript, tsx, python      D-02
wave 2  java, go, rust, swift                         D-05
wave 3  kotlin, scala, ruby, c, cpp, csharp           D-05
wave 4  the remaining tags.scm languages              D-25, dropped
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

`D-06` moved the port case forward. `T-21` names the collision error and the plan filed it under
`D-09`, the fleet registration row. The code that raises it is `server.py`, which is this row, so
the case is written and passing now and `T-21` names both rows. `D-09` still owns the five profile
files, and none of them is written yet.

`D-06` also revealed four cases the plan had no row for, so they are added rather than absorbed.
`T-61` and `T-62` are the stdio bridge, round trip and dead daemon. `T-63` is a project with no
graph, which is not an empty graph. `T-64` is `graphrag doctor`, the command the Integration
section names and no case covered.

`D-16` is an under-record the Components table carried from the start. It names `scope.py`,
`federation.py` and `peers.py`, and no task row owned them. They are the workspace half of the
engine, so they get their own row rather than being folded into a surface row that is finished.


# What `D-07` settled, 2026-08-27

The watcher runs in the daemon, not beside it. `server.py` starts it in the lifespan and stops it on
shutdown, and `/healthz` carries `watching` next to `worker_alive`. A dead watcher belongs to the
thread and to no project row, so nothing else would report it: a fleet that simply stopped changing
looks identical to one nobody edited.

`watchfiles` is the one dependency the step added. The debounce happens in Rust before Python sees
the batch, so a `git checkout` across four thousand files crosses into Python once. A raw inotify
reader would queue four thousand passes for one project.

The watcher shares `filters.language_of` and `filters.skipped_dir` with the indexer, and it stats
nothing. A deleted file cannot be stat-ed, and the pass that follows is what notices the deletion,
so passing a size here would drop exactly that event.

`T-16` was corrected in the same commit. The test plan carries the reason: resolution is global, so
a pass reparses the tree rather than the edited file, and what the watcher guarantees is one pass
per project rather than one per file.

# What `D-35` to `D-38` settled, 2026-08-30

The maintainer deleted the encyclopedia in `largest-enrolled-project` and ruled that the two search engines answer in
its place. That holds only if both reach the code. This one reached zero Acme repositories:
its federation was declared, and the workspace declared nothing.

So `federation.links` walks the root with `os.walk(followlinks=False)`, bounded at four levels, and
resolves each symlink with `strict=True`. It never descends into a link, because the target is
enrolled as a project of its own. The set is deduplicated by resolved target: that tree reaches 360
targets through many more links. `members:` still adds to the walk.

`federation_exclude` replaces the operator's veto, and it is matched against the link path and the
resolved target. Both, because `*/_worktrees/*` describes only the target, and matching the link
alone re-admits every second checkout of a repository already reached under its own name.

`exclude` and `languages` were parsed, type-checked and read by nothing, which is the exact failure
`projcfg.py` says it refuses. Both reach `discover.enumerate_files` now, and the walk prunes an
excluded directory rather than walking it to discard each file. It is load-bearing at fleet scale:
`gen2-php-app` indexes 5,994 files with no excludes, and about 1,400 once CodeIgniter's `system/`,
`application/third_party/` and the vendored `public/js/` are cut.

Removal became automatic, which overturns the registry rule against pruning a missing path. That
rule is right about a scan and wrong about a delete event, and `prune.py` acts only on the event. A
parent-exists test separates a deleted repository from an unmounted volume, and a 30 s grace period
absorbs a checkout into a moved-aside path. A removed symlink is the weaker case: it releases one
root's claim, so a member two roots reach keeps its row.

`find_symbol` spans `federation.expand(root)` and tags each hit with its project. Enrolment alone
left every question answering from the workspace's own scripts, because `_connect` opens one store
and the caller had to already know which of 360 repositories held the symbol. Cross-project edge
traversal stays out: node ids are per-store, and these services talk over gRPC and events, so no
call edge crosses a repository boundary to begin with.

# What `D-39` settled, 2026-08-30

The live proof of the automatic removal failed, and the fault was not in `prune.py`. Two throwaway
projects were enrolled with `graphrag index` against a running daemon, and neither reached the watch
set. One was then deleted, and no event fired, because nothing watched it.

`rearm_if_changed` was correct and nearly uncalled. Its one caller was the watch loop, on the branch
that runs after a prune removed something. The reference engine calls the same function from four
places, two of them enrolments, and the port took the function without them.

`graphrag index` widens the gap. It runs the pass in the operator's own process, so the daemon is
not late to hear about the new row. It is never told.

So `enroll` re-arms, which covers the MCP tool and the daemon's own route, and the watch loop
re-arms on every tick, which covers the CLI and any other writer. The tick runs once a second and
`_roots` parses every row, so `rearm_if_changed` stats the registry first and returns on an
unchanged mtime and size.

The quiet half is the one that had to be found this way. A project whose changes go unindexed
answers stale and a person notices. A project whose deletion is never seen answers nothing, and
`D-37` was live and unreachable for every row the daemon did not write itself.

`doctor --prune` still owns what neither reaches. inotify has no replay, so a project deleted while
the daemon was down leaves a row for a path `_roots` filters out, and no event can ever remove it.

# What the fleet pass measured, and what `D-40` owes, 2026-08-30

The first pass over 367 projects is also the first measurement of resolution at this scale. Two
numbers came back, and both are worse than the capability table reads.

An IMPORTS edge exists in 7 stores of 367, and every one of the 7 is Python or Java. The fleet holds
2,435 of them against 3.76 million edges. 67.2% of all 2,784,438 CALLS edges carry
`evidence: external`, which means the target resolved to nothing. Per generation the external share
runs 70.0% on Gen-1 `gen1-php-app`, 75.2% on Gen-2 `gen2-php-app`, 90.0% on Gen-4 `go-monorepo` and above 94% on
both Gen-3 samples.

One cause carries both. `module_name` spells a module by dotting a file path. An import row keeps
whatever the language wrote, which is a slash path with a repository prefix in Go and a backslash
namespace in PHP. The two agree in Python and in Java, and nowhere else. So `import_edges` finds no
target, and `_receiver_modules` narrows the pool to an empty set, which `resolve_reference` reports
as external.

The capability report is honest about the half it measures. An import **query** does exist for php,
go and javascript, and it does extract rows. Nothing then measures whether a row matched, so no
`gaps` entry names the difference.

`D-40` is the fix, and it is not bought here. It is recorded in
[module identity is Python-shaped](../knowledge/defects/module-identity-is-python-shaped.md) so the
workflow's limit is written down rather than discovered by a reader who takes an empty `callers`
list as proof that nothing calls a symbol.

# What `D-15` settled, 2026-08-27

The strip runs in `module_name` and in `resolve_module`, not in the first alone. A relative import
resolves against the importing directory, so a stripped module name compared against an unstripped
directory matches nothing, and scoping goes quiet on the languages the row exists to fix.

The longest prefix wins, or `src` eats the maven layout halfway and leaves `main.java.com.acme`.
A path that strips to nothing keeps its own parts, because an empty module name is shared by every
file sitting directly under a source root.

# What `D-16` settled, 2026-08-27

Members were declared in `.graphrag.yaml` and never discovered. The reason recorded here was that a
graph answers about a named symbol, so an undeclared member adds candidate definitions the operator
never chose and cannot see in a config file. `D-35` overturned it on 2026-08-30.

`sweep` claims a member the reachable set gained and releases one it lost. A member is an indirect
claim, so releasing the root releases it, while a member also enrolled on its own keeps its row.

`scope.owner` answers with the deepest enrolled root rather than the first. A project vendored
inside another is the more specific answer for its own files, and filing them under the outer root
loses the distinction the two rows exist to hold.

`peers.of` is best effort by construction. A short-lived client is gone before the lookup runs, and
`unknown` is the honest result. The daemon serves every session on the machine, so a ledger row
naming no caller names nothing useful.

# What `D-11` settled, 2026-08-27

`Type=notify` is the line the row exists for. The daemon sends READY after the worker runs and the
queue is served, so systemd reports started only when the process can answer. Without it the first
session's tool call lands on a daemon that accepts it and does nothing with it.

The caps are lower than the semantic engine's, and that is deliberate. Two indexers now compete with
the editor for the same cores, so the second one to arrive takes the smaller share: `MemoryHigh=2G`
against 4G, and a heavier `Nice`.

`reach.py` is the other half, and it is the larger one. A SessionStart hook stands in a directory
and speaks plain HTTP, because it carries no MCP client roots and cannot call a tool at all. Four
variants, and the unreachable one is the reason the module is not a one-line POST: it says the graph
is unavailable and structural questions are unanswered. It never says nothing calls the symbol.

The notice also carries the capability line, so a session learns before it asks which languages here
answer a caller question. A gap met as silence is the failure this engine exists to avoid.

`graphrag doctor` runs under `SuccessExitStatus=0 1`, because a doctor that finds a problem is a
finding and not a unit failure. Treating exit 1 as a failure pages for the report rather than the
fault.


# What `D-09` and `D-10` settled, 2026-08-27

Both rows own paths in the `claude-code-workflows` checkout, so the gate skips their anchors and
this section is the record instead. The engine was proven before the name was registered, which is
the order the plan fixes: one commit per repo, `ccw` last.

The roster held one element until today. `RequiredMCPServers` now names `graphrag` on 8766 beside
`coderag` on 8765, and the merge needed no change for a second name. The port was checked free and
checked for a tombstone before the line landed, because the first URL a name is seeded with is
permanent and only a tombstone round trip undoes it. The daemon answered on 8766 before the roster
line was written.

Every risk lived in code shaped around one server, and each piece is now a set or a parameter.
`ServerRegistered` takes the name. `Guard.Project` resolves against either registry, so a repo
enrolled only here is gated rather than exempt. The `PostToolUse` matcher covers both tools.

`searchFailed` learned the structural empty shape, `"results":[]`. Without that a graph miss reads
as a successful retrieval and buys the walk marker. That is the exact failure the `PostToolUse`
move was made to prevent. The correction below records what the shape is not.

One thing the gate could not share is the denial text. The structural registry carries no chunk
count, so the sentence that quotes one now branches on which registry answered. A gate that states a
number the engine never held is the failure it exists to stop, printed by the gate itself.

The gate accepts either engine and the order is doctrine. Five doctrine lines carry it: the four
the plan drafted, plus the loader line that names the `ToolSearch` query. Each names a capability
boundary rather than a second claim to be called first. The recorded contest says
three escalations of "call this first" all lost to grep.

# What `D-17` settled, 2026-08-27

The reach hook reads the registry row and never the store. `graphRegistryRow` in ccw unmarshals
`node_count`, `edge_count`, `resolved_edge_count` and `capabilities`, and `ProjectEntry.to_json`
emitted none of the four. Every indexed project therefore reported an empty graph, in the notice
built to keep a session from reading silence as an absence.

`ProjectEntry` now carries the four. `index.record(report)` writes them, and both the worker and
`graphrag index` call it. The CLI path wrote no row at all before, so an operator index left
`last_indexed` at zero.

An unchanged pass writes no graph, so `record` passes no counts and the row keeps what the last
real pass left. Zeroing there would report a live graph as empty, which is the same defect one
layer down.

# What `D-18` measured, 2026-08-27

`J-08` was the one journey with no number behind it. The routing rule said coderag names the symbol
and graphrag walks the edges from it, and no record graded that.

Ten caller questions, scored at file granularity against a hand-verified ground truth over the whole
tracked tree. graphrag returns F1 0.743, coderag lexical 0.569 and coderag semantic 0.383. So the
second engine earns its process, and question 7 of the design plan does not arise.

The split under that number is the finding, and one figure hides it. Where the name is called only
through the module that defines it, graphrag returns precision 1.000 and recall 1.000. Where the
tree also carries the name as an attribute -- `list.append`, `Path.resolve`, `sqlite3.connect` --
precision falls to 0.412.

The cause is in `extract.py`. A member call records the attribute name and `is_member`, and the
receiver is discarded before resolution. So `registry.load()` and `projcfg.load()` are one name to
the resolver, and every `list.append` site resolves onto `ledger.append`. That is part A's
documented `expr.method()` limit, measured rather than argued.

A first ground truth scoped `tests/` and `scripts/` out, and it priced a correct answer as a false
positive. A caller in a test is a caller. The corrected scope moved graphrag from F1 0.518 to 0.743
and moved nothing about the engine.

`D-19` is what the number motivates, and it landed. `extract.py` now records the receiver, and
`resolve.py` reads it in two steps. A receiver that names an imported module narrows the pool to
that module. A receiver that names anything else, and is not `self` or its siblings, leaves the
repo and earns no edge. The second step is the one that pays: it is the difference between the two
runs recorded below.

# What `D-19` measured, 2026-08-27

The same ten questions, at commit `0e8ffd6`, after the receiver landed.

graphrag returns F1 0.913 against 0.573 for lexical retrieval and 0.411 for semantic. The
`distinctive` class holds at 1.000 on precision and recall. The `collides` class rises from
precision 0.412 to 0.711 and from F1 0.538 to 0.831, and recall reaches 1.000 on both classes.

Two rules were tried in order, and the numbers picked the second. Narrowing the pool to the module
the receiver names took F1 to 0.795. Refusing a receiver that names nothing the file imported took
it to 0.913. So the loser was deleted rather than kept behind a switch.

The price is sites, not recall. `T-07` refuses 43.7% of its scoped call sites on CPython, which is
part A's `expr.method()` share almost exactly, while the collapse ratio rises from 7.3 to 8.7 and
ambiguity falls from under 25% to 8.9%. Recall on the caller set stays 1.000, so nothing refused
there was a real call.

What is left is a receiver naming a local variable. No syntactic rule places it, and closing that
gap needs the type of the receiver. `D-08` now ships that overlay, and a project that opts
in gets a resolved edge at those sites from the indexer instead of a refusal.

# A correction `D-10` forced, 2026-08-27

The plan said the gate learns graphrag's empty shapes, `nodes: []` and `edges: []`. The engine
emits neither. `tools.py` returns a `results` key on every path, error paths included, and it
emits no top-level `nodes` list and no top-level `edges` list. The two needles matched nothing, so
a graph miss still bought the walk marker.

The shipped empty shape is `"results":[]`, and the gate already rejects it. The two dead needles
are deleted in the `ccw` checkout, which this row's `(ccw)` prefix marks as out of reach from here.

# A correction `D-02` forced, 2026-08-27

The design said the pin gives 68 grammars with a definition capture, 45 with a call capture and 17
with an implementation capture. Two of the three were wrong. Measured under the pinned pack: 68
grammars ship a `tags.scm`, and 67 of them define, 50 call and 17 implement.

`svelte` is the one tagged grammar with no definition capture. Its query names sections in markup,
so nothing it captures is a symbol. TypeScript and TSX gain calls from the JavaScript query they
concatenate, so the effective call count is 52 against a pack census of 50. That leaves 18 tagged
grammars with no call capture of their own, and 16 that answer no caller question at all.

`T-06` now names all five numbers in its title. It carried the title alone before, so a count could
move under it and no reader would see anything change.

# What `D-03` left open, 2026-08-27

Two resolution rules were promised, and one of the two ships.

Constructor-call resolution ships. A constructor capture records the class name, so `Foo()` scores
against the class definition and never against `__init__`. On a two-file probe the call resolves to
the `class Foo` symbol at the imported-symbol tier. `T-199` grades it since 2026-08-27, in both
directions: the call resolves to the class, and no call site anywhere names `__init__`.

The re-export transitive pass does not ship. `imported_names` maps a name to the module the import
statement names literally. A `Foo` re-exported by `pkg/__init__.py` from `pkg.internal` misses both
import tiers, and falls to the global tier at confidence 0.30. `D-22` is that gap, and it stays
open rather than reading as done.

# What `D-09` proved on a fresh device, 2026-08-27

The registration is five files and one of them is written per profile, so a claim that it works on
this machine is not a claim that it bootstraps. Both halves were run against a scratch `HOME` with
no `~/.claude-shared` in it. The receipt is `partc-fresh-device.json` under the receipt directory.

`ccw hook link-shared` alone exits 0 and writes nothing. It cannot create the shared store, so on a
fresh device it re-asserts a roster that is not there yet. `ccw install --apply --targets=claude`
creates the store and seeds five `.claude.json` files, each holding `coderag` and `graphrag`.

That is the ordering the plan named as a hazard, measured rather than reasoned. The installer
bootstraps and the hook maintains, and neither does the other job.

# What the plan pair skills earn, 2026-08-27

Seven planning skills were retired here for zero dispatches, so a skill that is never selected is
the failure this pair had to avoid. The receipt is `partb-skill-dispatch.json`.

Two headless sessions ran, in two scratch Python packages outside the fleet repos. Each one asked
for a test plan and named no skill. The one-file service dispatched nothing, which the skill's own
refusal condition demands. The six-module package read the tree, dispatched `test-plan`, and
followed the procedure.

One arm alone reads either way, and that is why there are two. A session that skips the skill on a
one-file service obeyed it rather than missed it. So the second arm is the whole evidence that the
skill can earn a dispatch at all. `scripts/headless_probe.py` wrote the receipt out of the
session's own tool stream, and `T-128` grades it.

# The four stop-and-ask decisions, settled 2026-08-27

The design named nine decisions an agent may not take alone. Four of them arrived in this pass.

Decision 9, the fleet enrollment, was put to the user and answered. Six projects are enrolled and
no others: `graph-search-engine`, `largest-enrolled-project`, `claude-code-workflows`, `rag-search-engine`,
`device-sync` and `smart-app`. That is 6 of the fleet's 149, so the second indexer carries a
named set rather than the whole disk. `~/.local/share/graphrag/projects.json` holds those six plus
the two probe fixtures the tests enroll.

Decisions 1 and 4 were resolved without the question being put, and the record says so rather than
reading as though each was asked. Decision 1, port 8766, was verified free before the first apply
and the daemon answers on it. Decision 4, amending the ccw naming policy, was taken in that repo
and the amended record is the evidence. Both are reversible in one commit, which is why neither
was worth stopping the pass for. Decision 5, the language order, was asked and answered as PHP,
then TS and JS, then Python.

# The edge kind that was named and never built, 2026-08-27

The design named seven edge kinds. `store.py` ships six, and `INHERITS` is the missing one.

One capture carries both questions. The pack emits `@reference.implementation` for a base class and
for an interface alike, so `queries.py` maps it to `IMPLEMENTS` and nothing else. A second kind over
one capture splits nothing, and it claims a distinction the grammar does not make. So `INHERITS` is
dropped rather than left open, and this is the record of the drop.

A grammar that emits a separate inheritance capture reverses this. The kind set in `store.py` is
where that reversal lands.

# The receiver that is an expression, 2026-08-27

`D-19` captured the receiver of a member call. It did not settle what an empty receiver means.

`extract._member` returns a member call with an empty receiver where the byte before the dot closes
a call. `Path(raw).resolve()` is that shape. `resolve._receiver_modules` read the empty string as
`the receiver decides nothing` and scored the whole pool, so every homonym in the repo became a
candidate. The two-engine measurement carried twenty false positives, and each one was this shape.

An empty receiver now empties the candidate pool, so the reference is external. That is the same
rule the design already states for a receiver naming a module the file never imported. Precision on
the colliding class rose from 0.596 to 1.000, and recall did not move.

`config.EXTRACTION_ALGORITHM` went from 2 to 3 in the same commit. A resolution rule is invisible to
the content-hash diff, so a live store answers the old rule until the number forces the wipe.

# The quiet window, 2026-08-27

`constraints/a-pass-waits-for-the-project-to-go-quiet.md` holds the ledger, the window and the cost.
`constraints/extraction-runs-at-306-files-per-second.md` holds what the pass now costs.

`T-16` asserts one pass per debounce window, which is the property the delay preserves rather than
the delay itself. `T-214` and `T-215` cover the delay: a further save restarts the countdown, and
an explicit call pulls the waiting job forward. Both drive `index.Queue` rather than inotify,
because the restart is a queue rule and the watcher only supplies the delay.

# The receipt that graded a run nothing asserted over, 2026-08-27

A receipt is written before the assertions on purpose, so a run that moves a number leaves the
artifact rather than only a red test. Nothing then said which kind of run had written it. A failed
run left numbers on disk that read exactly like a measurement.

Three holes fed one bad artifact. `coderag_files` returned an empty set on a failed search, and an
empty set scores F1 0.0, so an unreachable daemon read as an arm that found nothing. The skip guard
proved the CLI was on PATH and never that the daemon answered. And the case reindexes the working
tree while the receipt stamped `commit_sha` alone, so a dirty tree measured code the SHA did not
name.

`provenance` now stamps `tree_dirty` beside `commit_sha`, and `outcome` says `unverified` until the
assertions have run over the numbers. The attester reads the receipt and never the tree, which is
the separation `decisions/a-measurement-is-an-attested-computation.md` argues for, so the tree state
has to travel inside the artifact to reach it.

`receipt_lock` gives one writer per node ID, and `write_receipt` replaces the file in one step. The
name is a pure function of the node ID, so two runs share one path, and a second run now refuses
rather than clobbers.

An audit of this row found two of the four writers short. `scripts/partc_probe.py` and
`scripts/headless_probe.py` took the atomic write and never the lock, so two probes of one node ID
could still race. Both now write through a `_write` helper that holds `receipt_lock`.

`check_attester_contract.py` gained the reverse direction. It checked that every receipt field was
declared. A concept that under-declares ships a run whose artifact its own attester rejects.
