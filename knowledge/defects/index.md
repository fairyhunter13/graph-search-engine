# Defects

* [The newest ledger row was not first](the-newest-ledger-row-was-not-first.md) - a rounded
  timestamp plus a stable sort handed back the older row of a tied pair.
* [scip-python drops cross-package references and exits
  0](scip-python-drops-references-and-exits-zero.md) - On a src layout it silently drops every
  cross-package reference, and a failed analysis is retried 100 times and then dropped. Every one
  of those paths writes an index and exits 0, so the coverage guard is the only thing that reads
  the difference.
* [The attester graded a literal](the-attester-graded-a-literal.md) - `D-19` moved the number
  in one of seven places, and the receipt the attester grades was a literal in test source.
