---
type: Attested Computation
resource: src/graphrag/resolve.py
title: Import scoping collapses the candidate set by roughly seven times
description: "The measurement the whole resolution design rests on. Global name matching gives 10.86 candidate files per call site on the pinned corpus, and import scoping gives 1.49."
tags: [resolution, measurement, cpython, attestation]
status: stable
runtime: python
generated: { by: claude/opus-5, at: 2026-08-27T06:12:26Z }
parameters:
  - { name: corpus, type: path, required: true }
executor:
  resource: ../skills/run-pytest-measure.md
  receipt: [test_node_id, corpus_ref, commit_sha, mean_global, mean_scoped, n_files]
attester:
  resource: ../attesters/measurement_equality.py
verified:
  - { by: process:okf-verify, at: 2026-08-27T09:32:43Z }
sources:
  - id: cpython-measure
    resource: https://github.com/python/cpython/tree/v3.12.7/Lib
    last_modified: 2026-08-27T00:00:00Z
  - id: resolve-module
    resource: src/graphrag/resolve.py
---

# The claim

A call site names a symbol. Matching that name against every definition in the repo gives 10.86
candidate files, and 54.5% of sites carry more than one.[^cpython-measure] Scoping the match to what
the file imports gives 1.49 candidates and 17.7%. That is a collapse of 7.3 times, and it is what
makes a ranked answer worth reading.

# Computation

```yaml
test_node_id: tests/test_resolve.py::test_import_scoping_collapses_candidates
corpus_ref: v3.12.7
```

The corpus is CPython at tag `v3.12.7`, the `Lib` tree with the test directory excluded, 755 files
and 53853 call sites. The test asserts the ratio and a wide band around each arm, never the two
numbers.[^resolve-module] A corpus at another tag moves both arms together, and the ratio is what
the design claims.

# What the receipt is for

A passing test proves nothing on its own, because the assertion can move in the same commit as the
number it guards. The receipt carries the test node ID and the commit SHA, so a deterministic
attester re-reads both and compares. That is the difference between a passing test and an attested
one.

# What would have to be true to revisit this

Import scoping stops beating global matching by six times on this corpus. Then the premise is gone,
`D-03` goes blocked with the observed numbers, and this concept is deprecated rather than relaxed.

[^cpython-measure]: CPython `Lib` at tag `v3.12.7`, 755 files, measured 2026-08-27.
[^resolve-module]: `mean_candidates` in `src/graphrag/resolve.py` is the measurement, one arm per call.
