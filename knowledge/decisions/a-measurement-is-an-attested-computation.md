---
type: Decision
resource: knowledge/computations/import-scoping-collapses-the-candidate-set.md
title: A load-bearing number is an Attested Computation, and its receipt carries the test node and the commit
description: "A passing test proves nothing on its own, because the assertion can move in the same commit as the number it guards. The receipt lets a deterministic attester re-read both and compare."
tags: [okf, attestation, measurement, verification]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T06:15:16Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
  - id: stamp-rule
    resource: https://github.com/fairyhunter13/claude-code-workflows
  - id: fleet-record
    resource: ../references/the-fleet-mechanisms-are-recorded-here-not-linked.md
---

# The problem the plan could not close

This project rests on measurements. The session that produced a number may not stamp it verified,
and the fleet hook enforces that: a request to mark something verified is a request to stamp, not a
confirmation that the claims hold.[^stamp-rule] So the measurement ended at a stamp the build cannot
write.

# Section 10 is the mechanism, and it was designed for this

Verification confirms that the definition still matches policy. It is document level, slow, and
recorded in the bundle. Attestation confirms that one run produced the value the sanctioned
way.[^okf-spec] It is per call, and it is not stored.

So a person verifies once that the measurement means what the plan claims. The attester confirms on
every run that the number came from the sanctioned computation. Neither substitutes for the other,
and the build owns the half it can own.

# What the receipt carries

The test node ID, the corpus ref, the commit SHA, and the numbers. The node ID and the corpus ref
are provenance, the numbers are fidelity, and the commit SHA is recorded rather than compared: a
sanctioned computation outlives the commit that last ran it.

# What would have to be true to revisit this

The attester stops being deterministic, or it needs a model call to reach a verdict. Then it is not
an attester any more, and this decision is replaced rather than loosened.

[^okf-spec]: OKF v0.2 section 10.6, on verification against attestation.
[^stamp-rule]: `EvaluateVerifiedStamp` in the fleet hook chain, arrived at independently of the
    spec. It lives in a private repository, so
    [the fleet record](../references/the-fleet-mechanisms-are-recorded-here-not-linked.md) carries
    what it does and this concept cites that.
