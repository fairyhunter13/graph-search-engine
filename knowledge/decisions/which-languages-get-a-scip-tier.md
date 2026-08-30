---
type: Decision
resource: src/graphrag/scip/run.py, src/graphrag/scip/__init__.py
title: Go and TypeScript get a SCIP tier, and every other language in this estate gets none
description: "Nine indexers are registered and three carry a command, but an operator can feed any of the nine by hand, so this is a decision and not a code limit. Measured over 372 stores: Go and TypeScript are kept, PHP and Python are refused, Java is deferred with one bounded experiment, and Vue is the wrong instrument entirely."
tags: [scip, decision, measurement, coverage, upstream, go, typescript, python, java, vue]
status: stable
generated: { by: claude/opus-5, at: 2026-08-30T00:00:00Z }
---

# What the engine offers, and what it does not limit

`run.py` registers nine indexers. Three carry a command, so the engine invokes them:
`scip-python`, `scip-typescript` and `scip-go`. The other six carry `command = ()`, and `run.run`
refuses them by name.

An empty command is not a closed door. `scip/__init__.py:86` reads `here / OUTPUT_NAME` first and
calls `run.run` only when that file is absent, so an operator can drop an `index.scip` at a unit
root and feed any of the nine by hand. That is the real adoption surface, and it is why every row
below is a decision rather than a report of what the code permits.

Three properties bound every ruling.

1. The overlay **rewrites and never creates** a call. `ingest._rewrite_call` returns False when
   tree-sitter recorded no call at that byte. A language whose tree-sitter query emits no call
   capture gains nothing from SCIP, however good the index.
2. The tier is opt-in per project, through `scip_indexers:` in `.graphrag.yaml`, because every
   live indexer needs a resolved build.
3. `ingest.coverage` refuses an index under 60% of the file census or 40% of the definition
   census, before any write. A collapsed index costs a project nothing.

# The estate, measured over 372 stores

`external` is that language's share of `CALLS`. The ceiling is the share of the `external` set
whose callee name is also defined in the same store, which is a generous upper bound because a
common short name counts.

| Language | Projects | Files | CALLS | `external` | Ceiling |
|---|---:|---:|---:|---:|---:|
| php | 333 | 65,369 | 1,779,393 | 76.7% | 33.7% |
| javascript | 119 | 7,708 | 827,535 | 42.4% | 70.8% |
| vue | 82 | 3,336 | 0 | — | — |
| go | 7 | 2,328 | 159,825 | 80.5% | 26.5% |
| typescript | 6 | 1,681 | 35,829 | 80.3% | 36.5% |
| tsx | 1 | 749 | 19,017 | 79.7% | 9.6% |
| python | 20 | 555 | 26,186 | 71.0% | 16.1% |
| java | 3 | 527 | 23,939 | 93.6% | 23.3% |
| sql | 4 | 299 | 0 | — | — |
| bash | 35 | 188 | 0 | — | — |
| rust | 1 | 2,439 | 47 | 100% | 0% |
| c | 1 | 2 | 28 | — | — |

Two facts change how the table reads.

- The go, typescript and tsx rows are measured **after** their overlay. Those ceilings are what
  SCIP left behind, and never what SCIP would win.
- `vue`, `sql` and `bash` sit at `tier='none'`. Every file is registered and hashed and none is
  parsed, so the zero is not a resolution failure. There is no graph to overlay.

# The ruling

| Language | Indexer | Upstream | Ruling |
|---|---|---|---|
| Go | `scip-go`, invocable, 0.2.7 installed | In the `scip-code` org, v0.2.7 of 2026-05-25 | **Keep** |
| TypeScript, TSX | `scip-typescript`, invocable, 0.4.0 installed | Frozen. No default-branch commit since 2025-10-02 | **Keep, and pin** |
| PHP | `scip-php`, no command | One maintainer, tags `v0.0.1` and `v0.0.2` only, open issue 862 says the published install crashes | **Refuse** |
| JavaScript | `scip-typescript` covers it with `--infer-tsconfig` | as above | **Refuse for now** |
| Python | `scip-python`, invocable, not installed | Last commit 2025-09-05, no release at all | **Refuse** |
| Java | `scip-java`, no command | In the `scip-code` org, active | **Defer, with one experiment** |
| Vue | none exists | — | **The wrong instrument** |
| C | `scip-clang`, no command | — | **Refuse twice over** |
| Rust, Ruby, Dart, Kotlin, Scala, C# | registered without a command, or absent | — | **Refuse** |

Go and TypeScript are kept because both are measured. Go moved from 90.0% `external` to 79.5%, and
26,747 of its 137,173 calls now read `evidence: scip`. TypeScript moved from 82.6% to 79.0%.

PHP is refused for reasons of its own, in
[php gets no scip tier and the resolver is the next buy](php-gets-no-scip-tier-and-the-resolver-is-the-next-buy.md).

JavaScript is the second language of the estate and the refusal is provisional. Its precondition is
an `npm install` in 119 projects, which is the same shape as the Composer problem that refused
scip-php. Measure that install cost before reopening it.

C is refused twice: 2 files, and C has no tree-sitter `calls` capability, so property 1 above makes
even a perfect index unwritable.

# Why Python is refused, which is the one new refusal

`scip-python` is invocable and unused, and that reads as an unfinished job. It is not.

Python is 20 projects and 555 files, and its ceiling is 16.1%. Both engine repos are registered
graphrag projects at 81 Python files each, and they measure 16.9% and 22.7%.

Both use a `src/` layout and neither carries a `pyrightconfig.json`.
[scip-python drops references and exits zero](../defects/scip-python-drops-references-and-exits-zero.md)
records that scip-python never sets `autoSearchPaths`, so on a `src/` layout Pyright resolves no
cross-package import and the index carries no cross-package reference. Cross-package is the whole
of what the overlay would buy here, so the buy is empty until someone writes the `extraPaths`
config, and the coverage guard still stands after that because the retry-and-drop half is unfixed.

Neither engine repo carries a `.graphrag.yaml`, so neither opts in today, and this refusal costs
nothing to hold.

# Why Java is deferred rather than refused

It is the cheapest test in the table. 93.6% `external` is the worst share measured anywhere, over
3 projects and 527 files, so the blast radius is small. `scip-java` has no command because no flag
set makes a Gradle project index itself, and the hand path needs no engine change.

The bounded experiment, if it is ever wanted: take the one Java project whose build resolves, run
`scip-java index` by hand, drop `index.scip` at the build root, add `scip_indexers: [scip-java]`,
re-index, and compare the `external` share. Set the stop rule at the 23.3% ceiling first.

# Vue is a gap in the extractor, not in the overlay

3,336 Vue files sit at `tier='none'`, which is the largest structural blind spot measured here.
`scip-typescript` reads no single-file component, and no `scip-vue` exists. Closing it needs a
tree-sitter grammar and `<script>` extraction from the SFC. An overlay cannot reach it, because
property 1 leaves nothing to rewrite.

Beside it, and also not a SCIP question: coderag holds 94 groovy projects and 427 gherkin files
that graphrag has no language for at all.

# TypeScript carries a supply-chain risk that Go does not

Both are adopted and both are measured, so the ruling is the same. The upstreams are not.
`scip-go` moved to the independent `scip-code` org and released in May 2026. `scip-typescript`
stayed under `sourcegraph` and has taken no default-branch commit since 2025-10-02. Its README
supports Node 18 and 20, and this machine runs Node v24.11.1, which is outside that matrix.

That is not a reason to drop it. It is a reason to record that the version in use is v0.4.0, that
no fix is coming, and that a Node upgrade is the thing most likely to break the tier quietly.

# The test to re-run before any future adoption

SCIP left Sourcegraph on 2026-03-25 for an independent project with a sponsor-led Core Steering
Committee. `scip`, `scip-go` and `scip-java` moved to the `scip-code` org. `scip-typescript`,
`scip-python`, `scip-clang`, `scip-dotnet` and `scip-ruby` did not.

**A repository that moved is the one being maintained.** That single test explains every row above,
and it is the fact to check again before reopening any refusal here.

Related: [scip is an overlay and never the extractor](scip-is-an-overlay-and-never-the-extractor.md),
[php gets no scip tier and the resolver is the next
buy](php-gets-no-scip-tier-and-the-resolver-is-the-next-buy.md).
