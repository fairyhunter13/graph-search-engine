---
type: Defect
resource: src/graphrag/cli.py, src/graphrag/registry.py
title: Prune wiped the graph but kept the directory
description: "`prune --apply` called `store.wipe`, which unlinks graph.db and its WAL sidecars but leaves the directory. `unclaimed_stores` counts a directory, so the count never reached zero and every run listed the same orphans."
tags: [prune, operations, registry, convergence]
status: stable
generated: { by: claude/opus-4.8, at: 2026-08-28T00:45:00Z }
sources:
  - id: prune
    resource: src/graphrag/cli.py
  - id: sweep
    resource: src/graphrag/registry.py
  - id: case
    resource: tests/test_registry.py
---

# What was wrong

`cmd_prune --apply` deleted a graph by `store.wipe(path / "graph.db")`.[^prune] `wipe` unlinks
`graph.db`, `-wal` and `-shm`, and nothing else. `index` reuses `wipe` to rebuild a graph in place,
so it must keep the directory. So prune left an empty directory behind.

`unclaimed_stores` counts a directory, not a graph: it returns every child of `INDEX_DIR` no row
claims.[^sweep] The empty directory still counted. `prune --apply` reported the orphan `deleted`,
`healthz` still showed it unclaimed, and the next `prune` listed the same directory. The count could
not reach zero. `forget` leaks a directory the same way, and relies on prune to sweep it. The
semantic engine's `forget` leaves a store for its `doctor --prune` too.

Found in production: 165 orphan stores in the semantic engine and 4 here, all live-suite fixtures.
The semantic engine's prune `rmtree`s and reached zero. This one did not.

# What holds it now

`registry.prune_unclaimed` walks `INDEX_DIR` and `rmtree`s each unclaimed directory under one
exclusive lock.[^sweep] The lock spans the walk and the delete together. A claim that landed between
them would build the graph the delete then removes. The semantic engine's prune already carries that
incident. `cmd_prune` calls it and reports the returned paths.[^prune] The dry run still lists
through `unclaimed_stores`.

A case in `tests/test_registry.py` builds one claimed store and one orphan. It prunes, and asserts
the orphan directory is gone. The claimed one stays, and `unclaimed_stores` is then empty.[^case]

[^prune]: `cli.cmd_prune`.
[^sweep]: `registry.prune_unclaimed` and `registry.unclaimed_stores`.
[^case]: `tests/test_registry.py::test_prune_removes_the_directory_so_the_count_reaches_zero`.
