# Decision

* [A load-bearing number is an Attested Computation, and its receipt carries the test node and the
  commit](a-measurement-is-an-attested-computation.md) - A passing test proves nothing on its own,
  because the assertion can move in the same commit as the number it guards. The receipt lets a
  deterministic attester re-read both and compare.
* [A member is declared in the project config and never discovered by a
  walk](a-member-is-declared-and-never-discovered.md) - The semantic engine finds members by walking
  symlinks under the root. A graph engine will not, because an undeclared member adds candidate
  definitions the operator never chose.
* [A project registers by claim, keyed on its resolved path, and a row leaves only on
  request](the-registration-surface-is-a-claim-and-a-row-leaves-only-on-request.md) - The fleet
  registry keys every row on the resolved path, counts the claims a row carries, and never prunes a
  row for a missing path.
* [A stale date is declared only where a re-measurement date is
  real](a-stale-date-is-declared-only-where-a-remeasurement-is-real.md) - Reachability beats a
  calendar. The nightly sweep catches a moved page, a rewritten commit and a deleted path, and a
  date with no owner and no runbook is a scheduled outage.
* [Resolution is import-scoped and ranked, and a single edge is never
  forced](resolution-is-import-scoped-and-ranked-and-never-forced.md) - The resolver matches a call
  site against what the file imports, and emits every survivor of the best tier with its own
  confidence.
* [SCIP is an overlay and never the extractor, because a symbol role carries no call
  role](scip-is-an-overlay-and-never-the-extractor.md) - SCIP names an occurrence and its roles, and
  no role is a call, so SCIP upgrades a call site rather than finding one.
* [The capture vocabulary belongs to the pack maintainer, so the pin is exact and a test grades
  every name](the-capture-vocabulary-is-the-maintainers-and-the-pin-is-exact.md) - The pack
  maintainer curates the tags queries, so the capture names drift with the pin, and every name is
  mapped or listed as ignored.
* [The project config is the SCIP opt-in, and the environment switch only
  subtracts](the-project-config-is-the-scip-opt-in-and-the-env-only-subtracts.md) - Two switches
  that both default off make the first one unreachable. The project asks for the overlay in its
  own config, and the environment variable exists so an operator can disable the tier on one
  machine.
* [The SCIP reader is a standard-library wire decoder, graded against
  protoc](the-scip-reader-is-stdlib-and-graded-against-protoc.md) - SCIP ships no Python binding.
  Generated code would add a runtime pin that has to move with it, for a tier that is off by
  default and reads eight messages. The wire format is frozen, so the decoder is the smaller
  liability.
* [The shrink gate grades warnings, because okf check exits 0 on a
  shrink](the-shrink-gate-grades-warnings-and-not-the-exit-code.md) - The plan named `okf check
  -against HEAD` as a gate. It reports a shrink as a warning and exits 0, and HEAD at push time is
  the tree it would compare. So the gate runs the same command against the upstream tip and grades
  what it prints.
* [tree-sitter is declined for chunking and adopted for graphs, because those are two
  questions](tree-sitter-is-declined-for-chunking-and-adopted-for-graphs.md) - The semantic engine
  rejected tree-sitter for chunking and dropped a graph tool with it, and that drop stands because
  this engine asks a different question.
