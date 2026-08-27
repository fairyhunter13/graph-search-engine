---
type: Constraint
resource: .githooks/pre-push
title: A stale date without an explicit UTC offset reads as fresh forever
description: "OKF section 5 wants an absolute instant. An offset-free value parses, passes the standard rule set, and turns freshness checking off with no error, so the gate here runs the strict rule set."
tags: [okf, gate, freshness, strict]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T06:15:16Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
    digest: sha256:26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101
  - id: okfrules
    resource: https://github.com/fairyhunter13/okf
---

# The value parses and then means nothing

`stale_after` is an absolute instant, so a comparison against it does not depend on when the file is
read. Upstream asserts the trap in its own tests: `is_stale` returns false for `2026-09-23` and for
`2026-09-23T00:00:00`.[^okf-spec] A date with no offset names a different instant in every
timezone, so the check declines to fire.

Nothing errors. The concept reads as fresh, and it reads that way forever.

# The strict rule set is the line that matters

`TimestampsCarryAnOffset` is a strict rule, and the fleet hooks run the standard set.[^okfrules] So
the trap is unguarded in every other repo here. This bundle is new and can be born clean, which is
the only cheap moment to opt in.

`T-31` proves it both ways. The strict arm rejects an offset-free date and the plain arm accepts the
same file. The second half is the evidence, and nothing else shows it.

[^okf-spec]: OKF v0.2 section 5, and the upstream `is_stale` assertions.
[^okfrules]: `doc_rules.go`, rule `TimestampsCarryAnOffset`, severity Strict.
