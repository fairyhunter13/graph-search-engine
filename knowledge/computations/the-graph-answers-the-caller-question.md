---
type: Attested Computation
resource: scripts/two_engine_measure.py
title: The graph answers the caller question, and only exactly where the name is distinctive
description: "The measurement that decides whether a second engine earns its process. Over ten caller questions the graph scores F1 0.743, coderag lexical 0.569 and coderag semantic 0.383, and the graph is exact only where the name is distinctive."
tags: [routing, measurement, two-engine, attestation]
status: stable
runtime: python
generated: { by: claude/opus-5, at: 2026-08-27T12:00:00Z }
parameters:
  - { name: corpus, type: path, required: true }
executor:
  resource: ../skills/run-two-engine-measure.md
  receipt: [test_node_id, corpus_ref, commit_sha, n_questions, f1_graph, f1_lexical, f1_semantic, f1_graph_distinctive, f1_graph_collides]
attester:
  resource: ../attesters/two_engine_receipt.py
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
this repo, scored at file granularity against a ground truth read by hand, give the graph F1 0.743
against 0.569 for lexical retrieval and 0.383 for semantic. So the second engine earns its process.

# The finding one number hides

Every question carries a class, and the classes disagree. Where a name is called only through the
module that defines it, the graph scores 1.000 on precision and 1.000 on recall. Where the tree also
carries the name as an attribute of something else, precision falls to 0.412 and F1 to 0.538.

The cause is in `extract.py`. A reference keeps the attribute name and discards the receiver, so
`registry.load()` and `yaml.load()` are one name in the graph.[^extractor] That is the `expr.method()` limit
this project documented from the start, and this is the first number on it.

# Computation

```yaml
test_node_id: tests/test_two_engine.py::test_the_graph_wins_the_caller_question
corpus_ref: graph-search-engine
```

The corpus is this repo's own tracked tree, `tests/` and `scripts/` included. A caller there is a
caller, and scoping it out prices a correct answer as a false positive.

The test asserts the ordering and the class split, never the digits. A number moves with the corpus,
and the corpus is the repo under work.

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

[^extractor]: `Reference` in `src/graphrag/extract.py` carries `is_member` and the attribute name only.
[^two-engine-run]: Ten caller questions over this repo, 58 ground-truth caller files, measured 2026-08-27.
