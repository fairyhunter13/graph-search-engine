---
type: Decision
resource: src/graphrag/projcfg.py, src/graphrag/scip/__init__.py, src/graphrag/index.py
title: The SCIP overlay is auto by language, and a project opts out
description: "Opt-in per project meant the overlay never reached a member repository, because writing a `.graphrag.yaml` into somebody else's checkout is not on offer. The overlay now runs for a language whose indexer is installed and needs no build the tree cannot resolve, unless `scip: false` says no."
tags: [scip, config, overlay, auto]
status: stable
generated: { by: claude/sonnet-5, at: 2026-09-25T00:00:00Z }
---

# The defect this corrects

`ProjectConfig.scip` defaulted to `False`, and `scip.enabled` required a project to set it `True`
before any overlay ran. A federated member is a repository nobody here owns, so a member with no
config of its own — most of the fleet — could never carry `scip: true`, and the overlay reached
only a project whose root explicitly asked. `graphrag doctor` reported `scip-go` as
`installable` in projects that held a `go.mod` and the binary on `PATH`, with nothing left to flip
it on.

# The rule

`ProjectConfig.scip` is `bool | None`, and `None` (the default, on every project that never sets
the key) means auto. `scip.enabled(project_scip)` returns `project_scip is not False and
config.SCIP_ENABLED`: `True` and `None` both leave the overlay eligible, and only an explicit
`False` opts out. `effective()` inherits the same three-value rule for a member: an inheriting
root's `True` wins over any other claiming root, `False` wins only where no claiming root sets
`True`, and the overlay is left auto where every claiming root is silent.

`scip.plan(conn, root, cfg)` decides which indexers actually run:

- Off entirely (`enabled(cfg.scip)` is `False`) returns `[]`.
- A project that names `scip_indexers` keeps that list exactly, install state included, because
  naming a tool is asking for its refusal to be reported rather than silently skipped.
- Naming none falls back to `scip.auto_indexers(conn, root)`.

`auto_indexers` selects an indexer at `readiness` tier `ready`, or at `installable` where the
indexer's own dependency marker (`deps` in `scip.run.Indexer`) is empty. `scip-go`'s dependency
resolves in a module cache the tree cannot see, so an installed `scip-go` against a `go.mod`
project is always selected. `scip-typescript` and `scip-php` name a marker
(`node_modules`, `vendor/autoload.php`), so they are auto-selected only where that marker is
already on disk — the overlay never runs `npm ci` or `composer install` to manufacture one. An
absent binary, a `manual` indexer with no command, and an `unconfigured` build unit are never
selected, matching the tiers a refusal already reported before this decision.

# Why a refused overlay still records its plan

`index.index_once`'s early return for an unchanged tree used to skip the overlay outright, so a
project already indexed before this change would never gain it: nothing about the tree changed to
re-trigger a whole pass. The unchanged-tree branch now recomputes `scip.plan` and compares its
joined name list against the `scip_indexers` meta row `_overlay` writes after every run. A plan
that differs from the stored one runs once, inside the same unchanged-tree return, and its result
is stamped back — so a fleet-wide config change, or a newly-installed indexer, reaches an
already-indexed project on its next save rather than waiting for a content change that may never
come. A plan that still refuses (the binary stays absent) writes the same meta it already held, so
the retry costs nothing until the indexer or the config actually changes.

Related: [scip is an overlay and never the extractor](scip-is-an-overlay-and-never-the-extractor.md),
[Go and TypeScript get a SCIP tier, and every other language in this estate gets
none](which-languages-get-a-scip-tier.md),
[the project config is the SCIP opt-in, and the environment switch only subtracts (deprecated
2026-09-25)](the-project-config-is-the-scip-opt-in-and-the-env-only-subtracts.md).
