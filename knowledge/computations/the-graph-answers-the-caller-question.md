---
type: Attested Computation
resource: scripts/two_engine_measure.py
title: The graph answers the caller question, and the retrieval index does not
description: "The measurement that decides whether a second engine earns its process. Over ten caller questions the graph scores F1 1.000, against 0.497 lexical and 0.306 semantic. The class split it once carried is closed."
tags: [routing, measurement, two-engine, attestation]
status: stable
runtime: python
generated: { by: claude/opus-5, at: 2026-08-27T08:30:23Z }
parameters:
  - { name: corpus, type: path, required: true }
executor:
  resource: ../skills/run-two-engine-measure.md
  receipt: [test_node_id, corpus_ref, commit_sha, tree_dirty, outcome, n_questions, f1_graph, f1_lexical, f1_semantic, f1_graph_distinctive, f1_graph_collides]
attester:
  resource: ../attesters/two_engine_receipt.py
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
stale_after: 2027-08-27T00:00:00Z
sources:
  - id: two-engine-run
    resource: scripts/two_engine_measure.py
    last_modified: 2026-08-27T00:00:00Z
  - id: extractor
    resource: src/graphrag/extract.py
---

# The claim

The routing rule says coderag names the symbol and graphrag walks the edges from it. No record
measured that, so the rule was argued and never graded.[^two-engine-run] Ten caller questions over
this repo are scored at file granularity, against a ground truth read by hand. They give the graph
F1 1.000, against 0.497 for lexical retrieval and 0.306 for semantic. So the second engine earns
its process.

# The finding one number hides

Every question carries a class, and the classes agreed only after two fixes. Where a name is called
only through the module that defines it, the graph scores 1.000 on precision and 1.000 on recall.
Where the tree also carries the name as an attribute of something else, precision is 1.000 and
F1 is 1.000.

The first run of this measurement put that second figure at 0.412. The cause was in `extract.py`:
a reference kept the attribute name and discarded the receiver, so `registry.load()` and
`yaml.load()` were one name in the graph. `D-19` captured the receiver.[^extractor] `D-27` then
refused the receiver that is an expression, which is what closed the rest.

# Computation

```yaml
test_node_id: tests/test_two_engine.py::test_the_graph_wins_the_caller_question
corpus_ref: graph-search-engine
```

The corpus is this repo's own tracked tree, `tests/` and `scripts/` included. A caller there is a
caller, and scoping it out prices a correct answer as a false positive.

The test asserts the ordering and the class split, never the digits. A number moves with the corpus,
and the corpus is the repo under work.

The arm figures also move between runs on one commit. Six runs span `d64e8fc`, `396f183`,
`1443efc`, `75bacf7` and `5f3495c`. They gave 0.535, 0.510, 0.510, 0.497, 0.497 and 0.497 lexical.
They gave 0.331, 0.316, 0.316, 0.306, 0.306 and 0.306 semantic. The graph scored 1.000 in every one. The retrieval
arms rank by an embedding over a live index, so read them as the scale of the gap and never as a
constant.

The last three agree to three digits, and the fifth ran while the `coderag` daemon was indexing 409
projects. The CLI stopped loading its own model between them, so the arms no longer compete with
the daemon for the card. See `references/the-coderag-cli-holds-its-own-gpu-session.md`.

# What the receipt is for

The ground truth is read by hand, so a score moves when the truth is edited and no engine code
changes. The receipt carries the test node ID and the commit SHA, so a deterministic attester
re-reads both and compares. The class figures are receipt fields for the same reason: a run
reporting one F1 hides the half where the engine loses.

# What would have to be true to revisit this

The graph stops beating both retrieval arms on a caller question. Then the second engine does not
earn its process, and this concept is deprecated rather than relaxed.

Or the receiver is captured and the `collides` class stops losing. Then the split is gone, one
number is honest, and the receipt shrinks with a new concept that names this one.

# What `D-19` did to the second clause, 2026-08-27

Half of it. The `collides` class stopped collapsing, and recall reached 1.000 on both classes. The
split did not close: 0.625 against 1.000 on precision. So the receipt keeps its class fields, and
this concept is amended rather than replaced.

The remaining loss is not a discarded receiver any more. It is a receiver naming a local variable,
which no syntactic rule places, and which this engine now refuses instead of guessing. Closing the
rest needs the type of the receiver, and that is what the SCIP overlay in `D-08` reads.

# What `D-27` closed, 2026-08-27

The other half. `Path(x).resolve()` has a receiver that is an expression, so `extract._member`
returned an empty receiver string. `resolve._receiver_modules` read empty as `decides nothing` and
scored the whole pool, which handed the edge to every homonym in the repo. Twenty false positives
in the `collides` class came from that one shape.

An empty receiver now empties the candidate pool, so the reference leaves the repo as external. The
`collides` class then scored 1.000 on precision, and the split this concept was written around is
closed.

The falsifier above says a closed split shrinks the receipt into a new concept. That is not
followed, and the reason is evidence. The class fields at 1.000 are what shows the split closed,
and a receipt without them cannot show it. So this concept is amended and the fields stay.

[^extractor]: `Reference` in `src/graphrag/extract.py` carries `is_member`, the attribute name and, since `D-19`, the receiver.
[^two-engine-run]: Ten caller questions over this repo, 70 ground-truth caller files, measured 2026-08-28 at commit `5f3495c`.
