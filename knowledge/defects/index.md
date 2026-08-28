# Defects

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
* [The overlay doubled its own edges](the-overlay-doubled-its-own-edges.md) - A call edge is keyed
  by its call site byte and replaces itself. An implements edge was keyed by nothing. A second
  ingest of one index inserted every one of them again, and the graph reported one interface twice.
* [An unreachable arm scored zero](the-unreachable-arm-scored-zero.md) - The two-engine receipt
  carried f1_lexical 0.0 against a claim of 0.412. Neither arm regressed: the coderag daemon was
  down, an empty result set scores zero, and the run wrote its receipt before the assertion that
  would have failed on it.
* [Prune wiped the graph but kept the directory](prune-wiped-the-graph-but-kept-the-directory.md) -
  `prune --apply` called `store.wipe`, which unlinks graph.db and its WAL sidecars but leaves the
  directory. `unclaimed_stores` counts a directory, so the count never reached zero and every run
  listed the same orphans.
