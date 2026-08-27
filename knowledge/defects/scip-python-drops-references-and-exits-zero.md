---
type: Defect
resource: src/graphrag/scip/ingest.py
title: scip-python drops cross-package references and exits 0
description: "On a src layout it silently drops every cross-package reference, and a failed analysis is retried 100 times and then dropped. Every one of those paths writes an index and exits 0, so the coverage guard is the only thing that reads the difference."
tags: [scip, guard, coverage, upstream]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T09:15:52Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T09:53:01Z }
sources:
  - id: scip-python-221
    resource: https://github.com/sourcegraph/scip-python/issues/221
---

# What happens

`scip-python` never sets `autoSearchPaths`, so on any `src/` layout Pyright resolves no
cross-package import and the index carries no cross-package reference.[^scip-python-221] Separately,
its `safe_analyze` swallows every analysis exception, retries 100 times, and then drops the file
with a console line.

# Why exit status cannot be the signal

All of those paths write an index and exit 0. An operator reading the exit code sees the same thing
after a complete run and after a run that lost most of the project.

# What holds it here

`ingest.coverage` counts the index against tree-sitter's own file and definition census before any
write, and `ingest.check` returns the reason a run is refused. Two floors, both a share of the
census: 60% of files and 40% of definitions. A refusal raises before the first `UPDATE`, so a
collapsed index costs the project nothing.

`T-19` is that case. A partial overlay is worse than no overlay, because every edge it does write
reads as `resolved` with `evidence = 'scip'` and confidence 1.0.

# The workaround, which does not replace the guard

Setting `extraPaths: ["src"]` in `pyrightconfig.json` fixes the first half. The guard stays,
because the second half is unfixed and because no operator sees the config of a machine they are
not on.
