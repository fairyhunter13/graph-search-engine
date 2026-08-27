---
type: Defect
resource: scripts/two_engine_measure.py
title: An unreachable arm scored zero, and a failed run left a receipt that read as a measurement
description: "The two-engine receipt carried f1_lexical 0.0 against a claim of 0.412. Neither arm regressed: the coderag daemon was down, an empty result set scores zero, and the run wrote its receipt before the assertion that would have failed on it."
tags: [attestation, measurement, provenance]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T21:50:00Z }
sources:
  - id: measure
    resource: scripts/two_engine_measure.py
  - id: engines-case
    resource: tests/test_two_engine.py
  - id: attester
    resource: knowledge/attesters/measurement_equality.py
  - id: concept
    resource: knowledge/computations/the-graph-answers-the-caller-question.md
---

# What happened

A receipt stamped `commit_sha: 8affff8` carried `f1_lexical: 0.0` and `f1_semantic: 0.0` against a
concept claiming `0.412` and `0.312`. It also carried `f1_graph_distinctive: 0.987` against a claim
of `1.000`. Three separate defects produced one file, and each one alone is enough to make a number
unreadable.

# Why nothing caught it

`coderag_files` ran `coderag search` with `check=False`, discarded stderr, and returned an empty set
where stdout carried no JSON. An empty set scores `f1 = 0.0`. So a daemon that did not answer was
recorded as an engine that found nothing, and the two are not the same claim. The skip guard was
`shutil.which("coderag") is None`, which proves the CLI is installed on PATH and says nothing about
the daemon behind it. A dead arm also makes `graphrag.f1 > lexical.f1` easier to pass, so the case
went greener as the evidence got worse.

The receipt is written before the assertions, on purpose: a run that moves a number should leave the
artifact rather than only a red test. Nothing recorded which of the two had happened.

The graph figure moved for a third reason. The case reindexes the working tree, and the tree held 62
uncommitted insertions including a new call to `grammars.capabilities` in `extract.py`. The TRUTH
row for that symbol named six caller files and the tree held seven, so a correct answer priced as a
false positive. `commit_sha` named a commit that did not describe the code that ran, and
`measurement_equality` reads a receipt rather than a tree, so no attester could see it.

# What holds it now

The arms raise on a non-zero exit and on unparsable output, carrying stderr. `arm_unreachable`
probes with one real search, so an unreachable daemon skips the case rather than scoring it.
`config.provenance` stamps `tree_dirty` beside `commit_sha`, and `outcome` says `unverified` until
the assertions have run and held. The attester refuses a receipt on either count, which keeps the
tree check inside the receipt where a consumer-side grader can reach it.

`config.receipt_lock` refuses a second concurrent run of one node ID, and `config.write_receipt`
replaces the file in one step. The two together retire the torn and clobbered receipt.

# What would have to be true to revisit this

TRUTH is read by hand, because a generated ground truth grades the generator. That is still right,
and it means any commit adding a call site to a symbol the table names moves the measurement. A
commit that touches such a call site has to re-read the row. Nothing mechanical can hold that
without becoming the generator the design rejects.
