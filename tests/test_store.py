"""T-01, and the rowid contract the FTS index depends on."""

from __future__ import annotations

import pytest

from graphrag import config, store


@pytest.fixture
def graph(tmp_path):
    conn = store.connect(tmp_path / "graph.db")
    yield conn
    conn.close()


def _one_node(conn, name: str = "retry") -> int:
    conn.execute("INSERT INTO files(path, mtime, size, sha256) VALUES('a.py', 0, 1, 'x')")
    file_id = conn.execute("SELECT id FROM files").fetchone()["id"]
    conn.execute(
        "INSERT INTO nodes(file_id, kind, name, start_byte, end_byte, start_line, end_line) "
        "VALUES(?, 'function', ?, 0, 5, 1, 1)",
        (file_id, name),
    )
    node_id = conn.execute("SELECT id FROM nodes").fetchone()["id"]
    conn.execute(
        "INSERT INTO nodes_fts(rowid, name, qualified_name, signature) VALUES(?, ?, '', '')",
        (node_id, name),
    )
    return file_id


def test_incompatible_meta_rebuilds(graph):
    """T-01. A graph stamped by an older algorithm is refused, with the reason.

    A boolean would be enough to trigger the wipe, and it would leave the
    operator guessing which pin moved. The reason is the whole return value.
    """
    assert store.incompatible(graph) == "the graph carries no algorithm stamp"

    store.stamp(graph, grammars="pack-1.15.8", queries="abc123")
    assert store.incompatible(graph, grammars="pack-1.15.8", queries="abc123") == ""

    store.set_meta(graph, "algorithm", str(config.EXTRACTION_ALGORITHM - 1))
    reason = store.incompatible(graph)
    assert "extraction algorithm moved" in reason
    assert str(config.EXTRACTION_ALGORITHM) in reason

    store.stamp(graph, grammars="pack-1.15.8", queries="abc123")
    assert store.incompatible(graph, grammars="pack-1.16.0") == "the grammar pin moved"
    assert store.incompatible(graph, queries="different") == "a query hash moved"


def test_deleting_a_file_takes_its_fts_rows_with_it(graph):
    """The failure this guards is not an error. It is a stale location.

    `nodes_fts` is external-content, so the cascade from `files` does not reach
    it. A search would keep answering with a symbol the graph no longer holds.
    """
    file_id = _one_node(graph)
    assert graph.execute("SELECT count(*) c FROM nodes_fts").fetchone()["c"] == 1

    store.delete_file(graph, file_id)

    assert graph.execute("SELECT count(*) c FROM nodes").fetchone()["c"] == 0
    hits = graph.execute("SELECT count(*) c FROM nodes_fts WHERE nodes_fts MATCH 'retry'")
    assert hits.fetchone()["c"] == 0


def test_the_unique_key_is_the_identifier_range(graph):
    """The join key SCIP ingestion upserts on, asserted before SCIP exists."""
    file_id = _one_node(graph)
    with pytest.raises(Exception, match="UNIQUE"):
        graph.execute(
            "INSERT INTO nodes(file_id, kind, name, start_byte, end_byte, start_line, end_line) "
            "VALUES(?, 'method', 'other', 0, 5, 1, 1)",
            (file_id,),
        )


def test_counts_report_the_resolved_share(graph):
    """The reach notice reports facts against guesses, so both are counted."""
    file_id = _one_node(graph)
    graph.execute(
        "INSERT INTO nodes(file_id, kind, name, start_byte, end_byte, start_line, end_line) "
        "VALUES(?, 'function', 'caller', 10, 16, 2, 2)",
        (file_id,),
    )
    ids = [r["id"] for r in graph.execute("SELECT id FROM nodes ORDER BY id")]
    graph.executemany(
        "INSERT INTO edges(src, dst, kind, confidence, candidate_count, resolved, evidence) "
        "VALUES(?, ?, 'CALLS', ?, ?, ?, 'import')",
        [(ids[1], ids[0], 0.85, 1, 1), (ids[1], ids[0], 0.3, 2, 0)],
    )
    assert store.counts(graph) == {"files": 1, "nodes": 2, "edges": 2, "resolved": 1}
