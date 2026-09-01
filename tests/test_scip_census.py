"""`scripts/scip_census.py`: the three arms, and the two refusals that bound them.

The arms touch 375 private repositories and write into a receipt directory CI
cats into a public log. Both of those are graded here and neither is graded by
running the fleet: the overlay's refusal and the receipt's anonymity are
properties of the code, and a test that needed the fleet would only ever skip.
"""

from __future__ import annotations

import importlib.util
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


census = _module(ROOT / "scripts" / "scip_census.py", "scip_census")


def test_a_worktree_groups_under_the_repository_it_belongs_to(tmp_path):
    """`T-333`. The denominator the committed table never stated.

    A worktree's `.git` is a file, and its `gitdir:` line names the main repo.
    Without this a repository with four worktrees is five roots to install into
    when it is one.
    """
    main = tmp_path / "main"
    (main / ".git").mkdir(parents=True)
    leaf = tmp_path / "leaf"
    leaf.mkdir()
    (leaf / ".git").write_text(f"gitdir: {main}/.git/worktrees/leaf\n", encoding="utf-8")

    assert census._family(leaf) == census._label(main)
    assert census._family(main) == census._label(main)

    alone = tmp_path / "alone"
    (alone / ".git").mkdir(parents=True)
    assert census._family(alone) == census._label(alone)


def test_a_root_reaches_a_receipt_only_as_a_digest():
    """`T-334`. CI cats the receipt directory into a log this repo publishes."""
    label = census._label("/some/private/path/to/a/repo")
    assert re.fullmatch(r"[0-9a-f]{12}", label)
    assert census._label("/some/private/path/to/a/repo/") == label
    assert census._label("/some/other/repo") != label


def test_the_overlay_arm_refuses_every_root_that_is_not_ready(monkeypatch, tmp_path):
    """`T-335`. `installable` is reachable only by installing into a foreign tree.

    `deps.resolve` never runs from this surface, so the population that would
    need one is unreachable rather than merely unvisited.
    """
    called: list[object] = []
    written: dict = {}
    roots = [tmp_path / "a", tmp_path / "b", tmp_path / "c"]
    standing = dict(
        zip(roots, ["installable", "unconfigured", "manual"], strict=True),
    )

    monkeypatch.setattr(census, "_enabled", lambda: roots)
    monkeypatch.setattr(census, "_languages", lambda path: ["typescript"])
    monkeypatch.setattr(
        census.run,
        "readiness",
        lambda path, langs: [{"indexer": "scip-typescript", "tier": standing[path]}],
    )
    monkeypatch.setattr(census, "apply_overlay", lambda *a, **k: called.append(a))
    monkeypatch.setattr(census, "_write", lambda name, body: written.update(body) or Path(name))

    census.overlay()

    assert called == []
    assert written["applied"] == 0
    assert written["refused_not_ready"] == 3


def test_the_share_arm_counts_the_stores_it_could_not_read(monkeypatch, tmp_path):
    """`T-336`. A fleet figure over an unstated population is not a figure."""
    live = tmp_path / "live"
    graph = tmp_path / "graph.db"
    conn = sqlite3.connect(graph)
    conn.execute("CREATE TABLE edges (kind TEXT, evidence TEXT)")
    conn.executemany(
        "INSERT INTO edges VALUES (?, ?)",
        [("CALLS", "scip"), ("CALLS", "same_file"), ("CALLS", "scip"), ("IMPORTS", "scip")],
    )
    conn.commit()
    conn.close()

    written: dict = {}
    monkeypatch.setattr(census, "_enabled", lambda: [live, tmp_path / "gone"])
    monkeypatch.setattr(
        census.config, "index_path", lambda path: graph if path == live else tmp_path / "no.db"
    )
    monkeypatch.setattr(census, "_write", lambda name, body: written.update(body) or Path(name))

    census.share()

    assert written["stores_read"] == 1
    assert written["stores_skipped"] == 1
    assert written["calls_total"] == 3
    assert written["scip_calls"] == 2
    assert written["calls_by_evidence"] == {"same_file": 1, "scip": 2}
