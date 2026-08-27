---
type: Policy
resource: .githooks/pre-push
title: This bundle is a strict profile of OKF v0.2, and a producer may be stricter than a consumer
description: "OKF v0.2 names no fixed taxonomy and forbids a consumer from rejecting a bundle over an unknown type. The gate here refuses one. The two are not in conflict, because the rule the spec writes is a rule for readers, and this repo is a writer."
tags: [okf, knowledge, gate, profile]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T06:09:50Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T09:53:01Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
    digest: sha256:26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101
  - id: okfrules
    resource: https://github.com/fairyhunter13/okf
---

# The spec is permissive on purpose, and it says so three times

Section 1 lists a fixed taxonomy of concept types as an explicit non-goal. Section 4.1 says type
values are not registered centrally, and that a consumer must tolerate an unknown type. Section 11
lists what a consumer must not reject a bundle for, and an unknown type is on that list.[^okf-spec]

Conformance is three rules. Every non-reserved file parses as frontmatter. Every frontmatter
carries a non-empty `type`. `index.md` and `log.md` follow sections 8 and 9. `type` is the only key
that is always required, so a concept carrying `type` alone is fully conformant.

# The gate here refuses an unknown type, and that is deliberate

`okfrules check -Werror` holds this bundle to a closed vocabulary of 17 names.[^okfrules] A push
fails on a type outside it. That is the point: `Constraints` for `Constraint` is a typo a reader
never notices and a grep never finds.

The checker knows it is deviating. Its own comment on `DefaultTypes` says the spec forbids this and
that the deviation must at minimum leave the four sample bundles the spec authors ship passing.
That is the bound, and it is a real one.

# A producer may be stricter. A consumer may not

This is the whole reconciliation, and it is one sentence. Section 11 constrains a reader of someone
else's bundle. This repo writes its own. Refusing to write an unknown type costs a reader nothing,
because the bundle a reader receives holds no unknown type.

So the rule to carry forward is narrow. Never loosen this gate to match section 11. Never write a
reader that rejects a bundle for the reasons this gate rejects a write.

# What would have to be true to revisit this

A type outside the 17 that this repo genuinely needs, and that upstream declines to add. The answer
then is to widen the vocabulary in the checker, not to drop the check.

[^okf-spec]: Read 2026-08-27. `SPEC.md` is byte-identical between the canonical repo and the frozen
    snapshot under `GoogleCloudPlatform/knowledge-catalog`.

[^okfrules]: v0.6.0. `rules/rules.go`, `DefaultTypes`.
