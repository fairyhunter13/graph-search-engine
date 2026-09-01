# Defects

* [A project is not one build](a-project-is-not-one-build.md) - `overlay` invoked each indexer
  once, at the project root. The Go monorepo holds eight `go.mod` files, so scip-go saw 2 of 2012 files,
  covered 0% and was correctly refused. The tier was unreachable for every monorepo.
* [A submodule is invisible to discovery](a-submodule-is-invisible-to-discovery.md) - `ls-files`
  lists a gitlink as one entry and never descends. 9 submodules were checked out at their pins and
  979 PHP files landed on disk. The node count, the edge count and the `external` share all moved
  by zero.
* [The newest ledger row was not first](the-newest-ledger-row-was-not-first.md) - append stamped
  ts rounded to a millisecond and read sorted with reverse=True. A stable sort keeps the original
  order inside a tie, so the older row of a tied pair came back first.
* [scip-python drops cross-package references and exits
  0](scip-python-drops-references-and-exits-zero.md) - On a src layout it silently drops every
  cross-package reference, and a failed analysis is retried 100 times and then dropped. Every one
  of those paths writes an index and exits 0, so the coverage guard is the only thing that reads
  the difference.
* [The attester graded a literal](the-attester-graded-a-literal.md) - `D-19` moved mean_scoped
  from 1.49 to 1.24 and one of seven copies was updated. The receipt the attester grades was a
  hand-written dict in test source, so it went stale with the claim and the two still agreed.
* [The overlay believed a stale artifact](the-overlay-believed-a-stale-artifact.md) - An occurrence
  is a byte range into the text the indexer read, and this tier writes at confidence 1.0. A file
  edited after the artifact holds different bytes at that range, so a span that still lands on a
  node is a wrong answer outranking every right one. A newer file now skips the document.
* [The overlay doubled its own edges](the-overlay-doubled-its-own-edges.md) - A call edge is keyed
  by its call site byte and replaces itself. An implements edge was keyed by nothing. A second
  ingest of one index inserted every one of them again, and the graph reported one interface twice.
* [An unreachable arm scored zero](the-unreachable-arm-scored-zero.md) - The two-engine receipt
  carried f1_lexical 0.0 against a claim of 0.412. Neither arm regressed: the coderag daemon was
  down, an empty result set scores zero, and the run wrote its receipt before the assertion that
  would have failed on it.
* [The daemon never saw a row another process wrote](the-daemon-never-saw-a-row-another-process-wrote.md) - `rearm_if_changed` had one caller, and it was not an enrolment. A row written by `graphrag index` was watched only after a restart, so its changes went unindexed and its deletion was never seen.
* [Module identity is Python-shaped](module-identity-is-python-shaped.md) - `module_name` dots a
  file path and an import row keeps the language's own spelling. They agree in Python and Java only,
  so 7 of 367 stores hold an IMPORTS edge and 67.2% of the fleet's CALLS edges land on external.
* [Prune wiped the graph but kept the directory](prune-wiped-the-graph-but-kept-the-directory.md) -
  `prune --apply` called `store.wipe`, which unlinks graph.db and its WAL sidecars but leaves the
  directory. `unclaimed_stores` counts a directory, so the count never reached zero and every run
  listed the same orphans.
* [The overlay had nothing left to upgrade](the-overlay-had-nothing-left-to-upgrade.md) -
  `_rewrite_call` upgraded a call site only where a stored `CALLS` edge sat at that byte. Query-time
  resolution stopped storing cross-file call edges, so the tier could upgrade only the same-file
  calls it adds least to. The guard now reads `refs` too, and the derived hop skips a site the tier
  already decided.
* [The overlay writes an FTS column and never the
  index](the-overlay-writes-an-fts-column-and-never-the-index.md) - `_upgrade_node` writes
  `qualified_name`, which `nodes_fts` indexes, and there is no trigger. It is correct today only
  because the pass runs the overlay one line before `rebuild_fts`. Recorded, not fixed: the per-file
  rewrite is what exposes it.
* [Reclaim never reclaimed a page](reclaim-never-reclaimed-a-page.md) - `PRAGMA auto_vacuum` read 0
  on 373 of 375 stores, so `incremental_vacuum` did nothing on any of them. The Gen-2 PHP app was 151 MB
  over about 9.7 MB of live data. The algorithm bump rebuilt every store, and the pragma took.
* [The overlay ran on every save](the-overlay-ran-on-every-save.md) - A one-file save on the Go monorepo was
  queryable after 34.7 s against a one-second criterion. The SCIP overlay was 49 s of a 58 s
  profiled pass: it re-ran the indexer and re-read 1.8 M occurrences for one changed file.
* [The isolation probe and the daemon did not run the same
  experiment](the-fleet-wide-arm-loses-roots.md) - **Retracted 2026-09-01.** Two projects were
  reported as receiving no watch event when 375 roots are armed in one call. All 375 roots hold an
  inotify watch, the descent covers every directory, and 362 of 375 projects have zero ledger rows
  because nobody edits them. The isolation probe wrote a file the daemon's filter refuses and the
  bare library run had no filter, so the two experiments were not the same experiment.
* [A generated bundle was indexed as source](a-generated-bundle-was-indexed-as-source.md) -
  The web tree's hottest callee name is the single character `n`, at 90,156 CALLS edges, and that
  one store holds 28.7% of every reference row in the fleet. A `.min.js` suffix test refuses none of
  the six bundles measured, because two of them are pretty-printed. The rule that holds it is
  distinct-trigram diversity over the bytes.
* [The plan pair described a gate that was gone](the-plan-pair-described-a-gate-that-was-gone.md) -
  `832b1bb` cut the plan-pair block from the pre-push hook and both `docs/test-plan.md` and `ci.yml`
  kept describing it. Three days later 6 `done` rows named tests that no longer exist, 4 owned paths
  named deleted files, 26 tests no row names, and 1 dev row covered nothing. The gate is now a test.
* [A tally written in prose had no gate](a-tally-written-in-prose-had-no-gate.md) - three audits in
  one day each corrected wrong figures in the same records, and each round wrote a new wrong one
  while fixing the last. Nine false claims. Every gate here passes a sentence that counts wrong,
  because none of them reads a number written in prose. `T-337` grades the one tally that drifted
  three times; the rest of the class is held by nothing but a reader who recounts.
