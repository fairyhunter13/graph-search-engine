---
type: Decision
resource: src/graphrag/scip/run.py
title: The SCIP tier reports its readiness before anything acts on it
description: "Five tiers -- ready, installable, unconfigured, manual, absent -- named per root by `run.readiness` and printed by `doctor`. Over 375 enrolled roots the estate reads 338 manual, 120 unconfigured, 21 absent, 9 installable and 2 ready, so the population an install helper serves is 9 roots and not the 16 estimated. The tier that had to be invented is `unconfigured`: without it a build-unit fallback read as a build unit and 121 TypeScript roots stood as installable when 119 hold no tsconfig at all."
tags: [scip, readiness, fleet, census, install]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: readiness
    resource: src/graphrag/scip/run.py
  - id: helper
    resource: src/graphrag/scip/deps.py
  - id: doctor
    resource: src/graphrag/cli.py
---

# What a tier says

`run.readiness` names, for one project, every indexer that would serve a language the project
actually holds, and where that indexer stands[^readiness]:

| tier | what stands between this root and a SCIP index |
|---|---|
| `ready` | nothing. The indexer is installed, the build unit is marked, the dependencies are on disk |
| `installable` | the dependencies. A bounded command fetches them |
| `unconfigured` | the build. The indexer needs a marker this project does not carry |
| `manual` | the project's own build. The indexer has no argv this engine will invoke |
| `absent` | the indexer. It is not on `PATH` |

`manual` is decided before `absent`, and the order is the point. An indexer with no command has no
program to look for, so reporting it as `absent` would read as a missing download and send an
operator to install a tool that would still not run here.

An indexer whose dependencies resolve outside the tree -- Go's module cache is the case -- reports
an empty `deps` marker and cannot reach `ready` from a filesystem read. It stands at `installable`,
because its install command is idempotent and running it is what settles a question the tree cannot
answer.

# The tier that had to be invented, and what found it

`run.units` returns the single empty prefix in two unrelated situations: an indexer that needs no
build marker, and a project holding none of the marker it needs. That collapse is correct for
`overlay`, which tries the root and lets the coverage guard refuse it. In a report it is a lie --
it reads as a build unit that is not there.

The first draft carried four tiers and read too well. Measured over the fleet it called 121
TypeScript roots `installable`. Separating the fallback out, 119 of those carry no `tsconfig.json`
anywhere in the tree, and the true count is 3. A report that overstates readiness by fortyfold is
worse than no report, because the number it produces is the one an operator would plan against.

# The estate, measured over 375 enrolled roots

| tier | indexer/root pairs | |
|---|---|---|
| `manual` | 338 | 333 php, 3 java, 1 rust, 1 c |
| `unconfigured` | 120 | 119 typescript, 1 go |
| `absent` | 21 | python; the indexer is not installed |
| `installable` | 9 | 6 go, 3 typescript |
| `ready` | 2 | typescript |

The reading is that this tier's ceiling over this estate is build configuration and not tooling.
Two thirds of the pairs are `manual`, and 333 of those are PHP -- see
[php-gets-no-scip-tier-and-the-resolver-is-the-next-buy](php-gets-no-scip-tier-and-the-resolver-is-the-next-buy.md),
whose refusal this measurement re-confirms over a population five times the size it was taken on.
Of the languages that can be served, the gap is a missing `tsconfig.json` in 119 roots, which no
helper this engine ships can supply.

# The helper is a separate surface, and that is the decision

`run.py` invokes an indexer and installs nothing. `deps.py` installs and indexes nothing[^helper].
Neither is reachable from an index pass, and only `deps.py` is off the operator command surface
entirely -- it is invoked by hand, `python -m graphrag.scip.deps <root>`.

A package manager executes code it has just downloaded. So `check` refuses any argv whose program
is `npm`, `pnpm`, `yarn` or `bun` and which carries no `--ignore-scripts`, and `plan` applies that
guard where the command is chosen rather than where it was written. The table is data, and data
drifts. The guard is keyed on the program and never on the presence of a flag, so `go mod
download` -- which runs no module's code -- is not refused for lacking a suppressor it does not
need.

Each run is recorded in a ledger beside the graph and never inside the project, for the reason
`config.index_path` already keeps the graph out: this engine indexes trees it does not own.

# What it cost, and what was cut

`cli.py` reached the 300-line ceiling exactly. The block is two lines there -- a lazy import and a
dict key -- because `readiness` lives with the table it reads.

Cut: a fleet-wide form of the report. `status` prints all 375 registry rows and is called often;
readiness costs one `rglob` per indexer per root, and paying that on every status read to answer a
question asked once is the wrong trade. The fleet figures above came from calling the same
shipped function in a loop.

Cut: inferring a `tsconfig.json` for the 119 roots that lack one. `scip-typescript` can be told to
infer one, and an inferred build is a build this engine invented -- the coverage guard would then
be grading a project against a configuration its own authors never wrote.

[^readiness]: `src/graphrag/scip/run.py`, `readiness` and `_standing`.
[^helper]: `src/graphrag/scip/deps.py`, `check` and `plan`.
