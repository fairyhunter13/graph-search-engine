---
type: Constraint
resource: src/graphrag/extract.py
title: Extraction runs at about 118 files per second, not 334
description: "The design quoted 334 files per second for a parse plus a tags query. This engine also normalizes captures, attributes scope and runs the import query, so it measures 117.8 on the same corpus and the floor is set from the measurement."
tags: [throughput, extraction, measurement]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T12:00:00Z }
sources:
  - id: cpython-lib
    resource: https://github.com/python/cpython/tree/v3.12.7/Lib
    last_modified: 2026-08-27T00:00:00Z
  - id: perf-case
    resource: tests/test_perf.py
---

# The measurement

CPython `v3.12.7`, 755 files of `Lib` with the test tree excluded, 12.2 MB.[^cpython-lib] Single
core, three runs, every file read into memory first so disk and decoding do not
count: 117.8, 117.8 and 117.9 files per second, and 1.9 MB per second.

# Why the design number does not apply

334 files per second timed a parse plus a tags query and nothing else. This engine runs three more
stages on every file: capture normalization over 58 names, scope attribution from the AST ancestors,
and the vendored import query. The two numbers measure different work, so the older one is not a
regression against this one.

# What the floor is for

`T-10` asserts 80 files per second, which is 32 percent under the measurement.[^perf-case] The floor
detects a regression and does not state a target. The margin absorbs a loaded machine, and a change
that costs a third of the throughput is a design change worth seeing.

# What would have to be true to revisit this

A corpus at another tag, another language mix, or a parallel pass. Cost was never a constraint on
this design: a 100k file repo is about 14 minutes on one core and under two on eight.

[^cpython-lib]: The pinned clone the measurement runs against, under `~/.cache/graphrag/corpus`.
[^perf-case]: `tests/test_perf.py::test_extraction_throughput_floor`, marked `corpus` and `slow`.
