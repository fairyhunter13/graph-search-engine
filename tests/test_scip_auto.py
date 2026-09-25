"""The SCIP overlay turns on by language unless a project says no.

`auto_indexers` picks a tool with no config at all: a language whose indexer
is installed and needs no dependency marker it cannot see, such as `scip-go`
against Go's module cache. `plan` wraps that with the project's own
`scip`/`scip_indexers` config.
"""

from __future__ import annotations

from graphrag import config, index, projcfg, store
from graphrag.scip import auto_indexers, plan, run


def _conn(repo_root):
    index.index_once(repo_root)
    return store.connect(config.index_path(repo_root), create=False)


def test_a_go_project_with_the_binary_installed_picks_scip_go(repo, monkeypatch):
    monkeypatch.setattr(run.shutil, "which", lambda name: f"/usr/bin/{name}")
    root = repo("go-proj", {"go.mod": "module x\n", "main.go": "package main\n"})
    conn = _conn(root)
    assert auto_indexers(conn, root) == ["scip-go"]
    conn.close()


def test_a_ts_project_without_node_modules_picks_nothing(repo, monkeypatch):
    monkeypatch.setattr(run.shutil, "which", lambda name: f"/usr/bin/{name}")
    root = repo("ts-proj", {"tsconfig.json": "{}\n", "a.ts": "const a = 1;\n"})
    conn = _conn(root)
    assert auto_indexers(conn, root) == []
    conn.close()


def test_a_ts_project_with_node_modules_picks_scip_typescript(repo, monkeypatch):
    monkeypatch.setattr(run.shutil, "which", lambda name: f"/usr/bin/{name}")
    root = repo("ts-proj2", {"tsconfig.json": "{}\n", "a.ts": "const a = 1;\n"})
    (root / "node_modules").mkdir()
    conn = _conn(root)
    assert auto_indexers(conn, root) == ["scip-typescript"]
    conn.close()


def test_an_absent_binary_picks_nothing(repo, monkeypatch):
    monkeypatch.setattr(run.shutil, "which", lambda name: None)
    root = repo("go-proj2", {"go.mod": "module x\n", "main.go": "package main\n"})
    conn = _conn(root)
    assert auto_indexers(conn, root) == []
    conn.close()


def test_scip_false_gives_no_plan_even_with_a_ready_indexer(repo, monkeypatch):
    monkeypatch.setattr(run.shutil, "which", lambda name: f"/usr/bin/{name}")
    root = repo("go-proj3", {"go.mod": "module x\n", "main.go": "package main\n"})
    conn = _conn(root)
    cfg = projcfg.ProjectConfig(scip=False)
    assert plan(conn, root, cfg) == []
    conn.close()


def test_named_indexers_win_over_auto_even_when_not_installed(repo, monkeypatch):
    monkeypatch.setattr(run.shutil, "which", lambda name: None)
    root = repo("go-proj4", {"go.mod": "module x\n", "main.go": "package main\n"})
    conn = _conn(root)
    cfg = projcfg.ProjectConfig(scip=True, scip_indexers=["scip-go"])
    assert plan(conn, root, cfg) == ["scip-go"]
    conn.close()
