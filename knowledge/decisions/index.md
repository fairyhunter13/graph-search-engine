# Decision

* [A build-free engine resolves at query time, and stores only what one file
  decides](a-build-free-engine-resolves-at-query-time.md) - No work that depends on more than
  one file may happen at index time. A same-file and a same-class reference is decided by its
  own file and stored as an edge; every reference that leaves its file is a `refs` row, scored
  on read. The memoized alternative was tested against the fleet and rejected: its
  invalidation input, the `IMPORTS` edge, exists in 7 of 375 stores.
* [A dead row takes its graph, and the delete is a move](a-dead-row-takes-its-graph-and-the-delete-is-a-move.md) - Dropping a row freed no disk: the graph directory waited for a hand-typed prune. The reaper now takes it, behind an idle floor `GRAPHRAG_PRUNE_MIN_IDLE_S` declared but never implemented, and the removal is a move into a week-long quarantine.
* [A load-bearing number is an Attested Computation, and its receipt carries the test node and the
  commit](a-measurement-is-an-attested-computation.md) - A passing test proves nothing on its own,
  because the assertion can move in the same commit as the number it guards. The receipt lets a
  deterministic attester re-read both and compare.
* [A member is discovered by walking the symlinks under the root, and declaration adds to
  it](a-member-is-discovered-by-walking-the-symlinks.md) - This engine declared its members until
  2026-08-30. A workspace reaching ~360 repos through a symlink tree drifts on the first repo added,
  so discovery replaced declaration and `federation_exclude` replaced the operator's veto.
* [A project registers by claim, keyed on its resolved path, and a row leaves only on
  request](the-registration-surface-is-a-claim-and-a-row-leaves-only-on-request.md) - The fleet
  registry keys every row on the resolved path, counts the claims a row carries, and never prunes a
  row for a missing path.
* [A row leaves on a delete event and never on a
  scan](a-row-leaves-on-a-delete-event-and-never-on-a-scan.md) - The registry refused to prune a
  missing path, because an unmount and a deletion look the same to a scan. They do not look the same
  to a delete event, so removal became automatic behind a parent test and a grace period.
* [A stale date is declared only where a re-measurement date is
  real](a-stale-date-is-declared-only-where-a-remeasurement-is-real.md) - Reachability beats a
  calendar. The nightly sweep catches a moved page, a rewritten commit and a deleted path, and a
  date with no owner and no runbook is a scheduled outage.
* [An absent directory is three answers and only one is a deletion](an-absent-directory-is-three-answers-and-only-one-is-a-deletion.md) - inotify has no replay, so a repository deleted while the daemon was down reaches no event. The cold-start reconciliation answers `deleted`, `unmounted` or `unknown` from the `st_dev` recorded at enrolment, reports by default, and acts on `deleted` alone.
* [Go and TypeScript get a SCIP tier, and every other language in this estate gets
  none](which-languages-get-a-scip-tier.md) - Nine indexers are registered and three carry a
  command, but an operator can feed any of the nine by hand, so this is a decision and not a code
  limit. Measured over 372 stores: Go and TypeScript are kept, PHP and Python are refused, Java is
  deferred with one bounded experiment, and Vue is the wrong instrument entirely.
* [The watcher hints which files changed, and the whole-tree scan
  reconciles](the-watcher-hints-and-the-scan-reconciles.md) - inotify already answers what changed,
  and `_submit` threw the answer away. The paths ride along as a hint now, so a save hashes those
  files and not the 2,461 of the Go monorepo. The hint never replaces the scan, because inotify has no
  replay and only the unhinted pass heals an event no process saw.
* [PHP gets no SCIP tier, PHPStan is deferred, and the resolver is the next
  buy](php-gets-no-scip-tier-and-the-resolver-is-the-next-buy.md) - `scip-php` is registered with no
  command, and it stays that way. It needs a Composer install no PHP tree in this estate has, and
  the generations where the miss is recoverable are CodeIgniter, which it cannot read. The measured
  corpus says fix the resolver instead.
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
  shrink](the-shrink-gate-grades-warnings-and-not-the-exit-code.md) - Deprecated on 2026-08-29 with the script. `okf check -against HEAD` reports a shrink as a warning and exits 0, so a gate had to grade the printed output. The reasoning still holds, and augment-never-shrink is instruction now.
  -against HEAD` as a gate. It reports a shrink as a warning and exits 0, and HEAD at push time is
  the tree it would compare. So the gate runs the same command against the upstream tip and grades
  what it prints.
* [tree-sitter is declined for chunking and adopted for graphs, because those are two
  questions](tree-sitter-is-declined-for-chunking-and-adopted-for-graphs.md) - The semantic engine
  rejected tree-sitter for chunking and dropped a graph tool with it, and that drop stands because
  this engine asks a different question.
* [An index pass rewrites only the files that changed](an-index-pass-rewrites-only-the-files-that-changed.md) -
  the whole-tree `DELETE FROM files` is gone, and the cascade from one file row now takes exactly the
  rows that pass writes back. It depends on query-time resolution: while a cross-file edge was
  stored, deleting one file destroyed edges pointing into it that the pass could not rebuild.
  `nodes_fts` takes no cascade, so the rewrite issues an external-content `'delete'` carrying the
  **old** column values before it drops the rows.
* [The transitive query buys no cache yet, and the measurement says where one would
  go](the-transitive-query-buys-no-cache-yet.md) - `blast_radius` at depth 3 measured on two
  corpora across three builds. The stage-1 redesign moved nothing; `D-40` raised p99 2.8 times
  against a reach that rose 8.5 times, so cost per reached node fell 8.9 times. No cache is
  written, and the one the plan drafted is the wrong instrument for what was measured.
