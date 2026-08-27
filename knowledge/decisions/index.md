# Decision

* [A load-bearing number is an Attested Computation, and its receipt carries the test node and the
  commit](a-measurement-is-an-attested-computation.md) - A passing test proves nothing on its own,
  because the assertion can move in the same commit as the number it guards. The receipt lets a
  deterministic attester re-read both and compare.
* [A stale date is declared only where a re-measurement date is
  real](a-stale-date-is-declared-only-where-a-remeasurement-is-real.md) - Reachability beats a
  calendar. The nightly sweep catches a moved page, a rewritten commit and a deleted path, and a
  date with no owner and no runbook is a scheduled outage.
* [A member is declared in the project config and never discovered by a
  walk](a-member-is-declared-and-never-discovered.md) - The semantic engine finds members by walking
  symlinks under the root. A graph engine will not, because an undeclared member adds candidate
  definitions the operator never chose.
