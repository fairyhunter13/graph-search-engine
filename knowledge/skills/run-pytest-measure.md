---
type: Skill
resource: tests/test_resolve.py
title: Run a pinned pytest measurement and return a receipt
description: "The run procedure behind every Attested Computation in this bundle. It runs one anchored test against the pinned corpus, reads the numbers out of the run, and returns the receipt fields the attester inspects."
tags: [okf, attestation, measurement, pytest]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T12:00:00Z }
---

# When to use

Use this before a bundle value is shown to a reader. A concept of type `Attested Computation` names
this file in `executor.resource`, and the value it carries is not displayed until the attester
returns a verdict of ok.

# Preconditions

The corpus is checked out at the ref the computation names. `graphrag.config.corpus_root` reports
where it lives, and an absent checkout skips the case rather than failing it.

The working tree is committed. A receipt records the commit the run happened on, and an uncommitted
tree has no such commit.

# Steps

Read the sanctioned computation out of the concept body. It names the test node ID and the corpus
ref, and nothing else in the run is negotiable.

Run that one node ID under the repo toolchain:

```sh
GRAPHRAG_NAME_BAN=none uv run pytest -q -m corpus <test_node_id>
```

Read the numbers from the run rather than from the concept. Record `mean_global`, `mean_scoped` and
`n_files` exactly as the run reports them.

Record `test_node_id` and `corpus_ref` as run, not as intended. A run against another ref is a real
finding, and rewriting it to match the concept destroys the only evidence of it.

Record `commit_sha` from `git rev-parse HEAD`.

# Post-conditions

The receipt carries every field in `attesters/measurement_equality.py`, and no other.

The attester returns ok. Where it does not, the reason names the field that disagreed, and that
disagreement is the result. Do not display the value to the user until the attester returns ok.

Never modify the computation. A test whose assertion moved in the same commit as the number proves
nothing, and the receipt exists to make that visible.
