---
type: Defect
resource: src/graphrag/filters.py
title: A generated bundle was indexed as source, and one held 28.7% of the fleet's references
description: "The web tree's hottest callee name is the single character `n`, at 90,156 CALLS edges. No rule refused a machine-written file, and a `.min.js` suffix test refuses none of the six bundles measured."
tags: [indexing, filters, minified, performance]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: filter
    resource: src/graphrag/filters.py
  - id: discover
    resource: src/graphrag/discover.py
  - id: guard
    resource: tests/test_perfile.py
---

# What is wrong

`filters.py` decided what to index from the path alone. A minified bundle is source by that test, so
it was parsed, and every one of its one-character identifiers became a node or a reference.

Measured over 375 stores, 2026-09-01:

| Store | `refs` rows | Share of the fleet |
|---|---|---|
| `web tree` | 992,526 | **28.7%** |
| `Gen-4 Go monorepo` | 304,697 | 8.8% |
| whole fleet | 3,461,224 | 100% |

The web tree's hottest callee is `n`, with 90,156 `CALLS` edges -- 9.6% of every call in that
store on one character. The next four are `s`, `a`, `isset` and `e`. `refs` is the table a caller
question reads on every call, so one generated tree owned the fleet's worst query.

# Why a name test does not close it

A suffix rule was the first draft, and the measurement refused it. Six real bundles in that tree
cross the cap, and `elfinder.full.js` and `shared-ui.js` are **pretty-printed**, so a line-length
test passes both. A bundle named `app.js` walks past a `.min.js` test without slowing down.

# What holds it now

zoekt's rule, which reads the bytes: a document holding more than 20,000 distinct 3-byte sequences
is machine-written, whatever it is named[^filter]. `T-261` asserts the refusal on content and names
the file `app.js` so the suffix path cannot pass it[^guard].

The scan is not free, at about 0.19 ms per KB, so running it over a whole tree would cost more than
the parse it saves. A 64 KB size threshold is the cheap first pass, and it is measured: every
hand-written source file in this repo holds under 2,800 distinct trigrams, and 1 file of 192 is
large enough to be read for the test at all. A file at or over the threshold is read once and serves
both the digest and the test[^discover].

# The limit of the rule, stated rather than left to be found

`livewire.js` is a 525 KB generated bundle holding 13,653 distinct trigrams, so the cap accepts it.
It sits under `vendor/`, which `SKIP_DIRS` already refuses, so it is unreachable today. The rule
catches the minified class, and not every generated file.

[^filter]: `filters.generated` and `filters.MAX_DISTINCT_TRIGRAMS`.
[^discover]: `discover._hash_and_body`, which reads a large file once for both.
[^guard]: `tests/test_perfile.py::test_a_generated_bundle_is_refused_on_its_content_and_not_its_name`.
