---
type: Constraint
resource: src/graphrag/extract.py
title: Extraction runs at about 306 files per second, and the query is compiled once per language
description: "The engine measured 117.8 files per second while it compiled a fresh query for every file. Compiling costs 3.82 ms against 0.58 ms to parse the file. One compile per language takes the same corpus to 306, and the floor is set from the measurement."
tags: [throughput, extraction, measurement]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T06:24:30Z }
sources:
  - id: cpython-lib
    resource: https://github.com/python/cpython/tree/v3.12.7/Lib
    last_modified: 2026-08-27T00:00:00Z
  - id: perf-case
    resource: tests/test_perf.py
---

# The measurement

CPython `v3.12.7`, 755 files of `Lib` with the test tree excluded, 12.2 MB.[^cpython-lib] Single
core, three runs, every file read into memory first so disk and decoding do not count: 303.7, 307.2
and 306.6 files per second, and 5.0 MB per second. The host carried a load average of 13 throughout,
so this is a busy-host figure and not a best case.

# What the compile cost

`_run` built a `ts.Query` on every call, twice per file. Compiling is 3.82 ms and parsing the file is
0.58 ms, so the pass was mostly compiling the same two query texts again. The query is immutable once
compiled and the cursor is the mutable half, so one compile per language is cached and a fresh
`QueryCursor` is built per call. The earlier 117.8 figure is that build, not another corpus.

A second cost sat beside it. A language whose capability set is empty has no definition capture, no
call capture and no import query, so its parse can only return an empty match set. `extract` returns
before the parse there. JSON alone is 96 percent of the files in one indexed tree, at 14.85 s a pass.

# Why the design number does not apply

334 files per second timed a parse plus a tags query and nothing else. This engine runs three more
stages on every file: capture normalization over 58 names, scope attribution from the AST ancestors,
and the vendored import query. The two numbers measure different work.

# What the floor is for

`T-10` asserts 200 files per second, which is 34 percent under the measurement.[^perf-case] The floor
detects a regression and does not state a target. The margin absorbs a loaded machine, and a change
that costs a third of the throughput is a design change worth seeing.

# What would have to be true to revisit this

A corpus at another tag, another language mix, or a parallel pass. Cost was never a constraint on
this design: a 100k file repo is about 5 minutes on one core.

[^cpython-lib]: The pinned clone the measurement runs against, under `~/.cache/graphrag/corpus`.
[^perf-case]: `tests/test_perf.py::test_extraction_throughput_floor`, marked `corpus` and `slow`.
