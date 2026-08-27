---
type: Skill
resource: scripts/two_engine_measure.py
title: Run the two-engine caller-question set and return a receipt
description: "The run procedure behind the routing-rule measurement. It runs one anchored test over this repo's own tree with both engines live, reads the scores out of the run, and returns the receipt fields the attester inspects."
tags: [okf, attestation, measurement, routing, two-engine]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T07:57:11Z }
---

# When to use

Use this before the routing-rule numbers are shown to a reader. The concept
`computations/the-graph-answers-the-caller-question.md` names this file in `executor.resource`, and
its value is not displayed until the attester returns a verdict of ok.

# Preconditions

Both engines are live. The `coderag` CLI is on the path and its daemon answers, and this repo is
enrolled in graphrag. An absent `coderag` skips the case rather than failing it, because one arm
scoring zero for the wrong reason is not a measurement.

The corpus is this repo itself, so the working tree is committed. A receipt records the commit the
run happened on, and an uncommitted tree has no such commit.

# Steps

Read the sanctioned computation out of the concept body. It names the test node ID and the corpus
ref, and nothing else in the run is negotiable.

Run that one node ID under the repo toolchain:

```sh
GRAPHRAG_NAME_BAN=none uv run pytest -o addopts= -q -m engines <test_node_id>
```

`-o addopts=` is load-bearing. `pyproject.toml` already sets `-q`, so a second one gives `-qq` and
the run prints no node ID at all.

The run writes the receipt itself, to `~/.cache/graphrag/receipts/`, named for the node ID. Read
that file. Never assemble a receipt by hand. A receipt typed beside the claim is a second copy of
the claim, and `defects/the-attester-graded-a-literal.md` records what that cost.

The two class figures are receipt fields for a reason. One number over the whole set hides the half
where the graph loses, and hiding it is the finding this computation exists to carry.

`test_node_id` and `corpus_ref` come from the run, not from the intent. A run against another tree
is a real finding, and rewriting it to match the concept destroys the only evidence of it.

`commit_sha` is the short SHA, because the concept's footnote names the run by a short SHA.

# Post-conditions

The receipt carries every field in `attesters/two_engine_receipt.py`, and no other.

The attester returns ok. Where it does not, the reason names the field that disagreed, and that
disagreement is the result. Do not display the value to the user until the attester returns ok.

Never modify the computation. The ground truth is read by hand, so an edit to it moves the score
without touching a line of engine code, and the receipt exists to make that visible.
