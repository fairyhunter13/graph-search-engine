"""The per-file index pass, and the content filter that keeps it affordable.

Every case runs a real pass over a real git repository. The claim of the stage
is that editing one file touches one file's rows, and a fixture that stubbed the
store would assert nothing about it.
"""

from __future__ import annotations

import hashlib

import pytest

from graphrag import config, discover, filters, index, indexwrite, store

TREE = {
    "a.py": "def alpha():\n    return 1\n",
    "b.py": "def beta():\n    return 2\n",
    "c.py": "def gamma():\n    return 3\n",
}


@pytest.fixture
def tree(repo):
    root = repo("perfile", TREE)
    index.index_once(root)
    conn = store.connect(config.index_path(root))
    yield root, conn
    conn.close()


def _nodes_of(conn, path: str) -> dict[str, int]:
    sql = (
        "SELECT n.id, n.name FROM nodes n JOIN files f ON f.id = n.file_id "
        "WHERE f.path = ? AND n.kind != 'module'"
    )
    return {r["name"]: r["id"] for r in conn.execute(sql, (path,))}


def test_editing_one_file_rewrites_that_file_and_no_other(tree):
    """T-256. The whole stage, as one assertion over node identity.

    A rewritten file's nodes get new ids, because the row was deleted and
    inserted. An untouched file's ids have to be the ones it already had, or the
    pass rebuilt the tree and only looked incremental.
    """
    root, conn = tree
    before = {path: _nodes_of(conn, path) for path in TREE}

    (root / "a.py").write_text("def alpha():\n    return 1\n\n\ndef delta():\n    return 4\n")
    report = index.index_once(root)
    assert report.parsed == 1

    after = {path: _nodes_of(conn, path) for path in TREE}
    assert after["b.py"] == before["b.py"]
    assert after["c.py"] == before["c.py"]
    assert set(after["a.py"]) == {"alpha", "delta"}
    assert set(after["a.py"].values()).isdisjoint(before["a.py"].values())


def test_the_fts_row_count_tracks_the_node_count(tree):
    """T-257. `nodes_fts` takes no cascade and there is no trigger, so the two
    counts agree only because the pass writes both. A drift is not an error: it
    is `find_symbol` answering with a location the graph no longer holds."""
    root, conn = tree

    def counts():
        return (
            conn.execute("SELECT count(*) c FROM nodes").fetchone()["c"],
            conn.execute("SELECT count(*) c FROM nodes_fts").fetchone()["c"],
        )

    nodes, fts = counts()
    assert nodes == fts

    (root / "a.py").write_text("def alpha():\n    return 1\n\n\ndef delta():\n    return 4\n")
    (root / "c.py").unlink()
    index.index_once(root)
    nodes, fts = counts()
    assert nodes == fts


def test_a_renamed_symbol_is_not_findable_under_its_old_name(tree):
    """T-278. The reason `forget_files` reads the rows before it deletes them.

    An external-content FTS5 `'delete'` is given the **old** column values. Given
    the new ones it leaves the old postings behind, and the symptom is a hit that
    resolves to nothing.
    """
    root, conn = tree
    hits = conn.execute("SELECT count(*) c FROM nodes_fts WHERE nodes_fts MATCH 'alpha'")
    assert hits.fetchone()["c"] == 1

    (root / "a.py").write_text("def epsilon():\n    return 1\n")
    index.index_once(root)

    hits = conn.execute("SELECT count(*) c FROM nodes_fts WHERE nodes_fts MATCH 'alpha'")
    assert hits.fetchone()["c"] == 0
    hits = conn.execute("SELECT count(*) c FROM nodes_fts WHERE nodes_fts MATCH 'epsilon'")
    assert hits.fetchone()["c"] == 1


def test_the_file_count_is_the_tree_s_and_carries_no_synthetic_row(tree):
    """T-280. `write_externals` gave the store one `<external>` file row, so
    `report.files` read one larger than the tree for every project."""
    root, conn = tree
    report = index.index_once(root, force=True)
    assert report.files == len(TREE)
    paths = {r["path"] for r in conn.execute("SELECT path FROM files")}
    assert paths == set(TREE)


def test_two_overlapping_identifier_ranges_are_not_both_written(repo):
    """T-268. `UNIQUE(file_id, start_byte, end_byte)` catches an exact repeat and
    never an overlap, and two symbol sources naming one identifier rarely agree
    to the byte. The reject is what keeps one identifier at one node."""
    root = repo("overlap", {"a.py": "def alpha():\n    return 1\n"})
    conn = store.connect(config.index_path(root))
    try:
        with conn:
            conn.execute("INSERT INTO files(path, mtime, size, sha256) VALUES('a.py', 0, 1, 'x')")
            file_id = conn.execute("SELECT id FROM files").fetchone()["id"]
        assert indexwrite._overlaps([(4, 9)], 4, 9) is True
        assert indexwrite._overlaps([(4, 9)], 6, 12) is True
        assert indexwrite._overlaps([(4, 9)], 9, 14) is False
        # The module node is zero-width at 0, so it claims nothing.
        assert indexwrite._overlaps([(0, 0)], 0, 0) is False
        assert file_id
    finally:
        conn.close()


def test_a_pass_that_rewrites_part_of_the_tree_does_not_checkpoint(tree, monkeypatch):
    """T-276. `wal_checkpoint(TRUNCATE)` is fsync-bound, and after this stage a
    pass runs on every save. The pages worth reclaiming are the ones a whole-tree
    rewrite freed, so that is the only pass that pays for the call."""
    root, _ = tree
    calls: list[int] = []
    monkeypatch.setattr(store, "reclaim", lambda conn: calls.append(1))

    (root / "a.py").write_text("def alpha():\n    return 9\n")
    index.index_once(root)
    assert calls == []

    index.index_once(root, force=True)
    assert calls == [1]


def test_a_store_this_engine_creates_can_give_its_pages_back(tree):
    """T-277. 373 of 375 stores read `auto_vacuum` 0 on 2026-09-01, so `reclaim`
    had never reclaimed a page on any of them. `connect` sets the pragma before
    the header is written, and the algorithm bump is what rebuilt every store."""
    _, conn = tree
    assert conn.execute("PRAGMA auto_vacuum").fetchone()[0] == 2


def _dense(size: int) -> str:
    """High-entropy text over a JavaScript alphabet, deterministic per byte."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$"
    digest = hashlib.sha256(b"seed").digest()
    out: list[str] = []
    while len(out) < size:
        digest = hashlib.sha256(digest).digest()
        out.extend(alphabet[byte & 63] for byte in digest)
    return "".join(out[:size])


def test_a_generated_bundle_is_refused_on_its_content_and_not_its_name(repo):
    """T-261. A bundle named `app.js` walks straight past a `.min.js` suffix test.

    One such tree held 992,526 reference rows, 28.7% of the whole fleet, and its
    hottest callee name was the single character `n`. The refusal is the trigram
    diversity of the bytes, so the name never enters it.
    """
    size = filters.CONTENT_SCAN_BYTES * 2
    handwritten = ("function alphaBetaGamma() {\n  return alphaBetaGamma;\n}\n" * 4000)[:size]
    root = repo(
        "bundles",
        {
            "app.js": f"var x = '{_dense(size)}';\n",
            "real.js": handwritten,
            "small.js": f"var y = '{_dense(1024)}';\n",
        },
    )
    found = {meta.rel_path for meta in discover.enumerate_files(root)}
    assert "app.js" not in found
    assert found == {"real.js", "small.js"}

    assert filters.generated(handwritten.encode()) is False
    assert filters.generated(_dense(size).encode()) is True
