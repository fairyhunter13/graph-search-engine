"""T-01, and the rowid contract the FTS index depends on."""

from __future__ import annotations

import pytest

from graphrag import config, store


@pytest.fixture
def graph(tmp_path):
    conn = store.connect(tmp_path / "graph.db")
    yield conn
    conn.close()


def test_a_new_graph_can_give_its_pages_back(graph, tmp_path):
    """Nothing ran a VACUUM here before, so a rebuild freed pages inside the file
    and never to the filesystem. `auto_vacuum` only takes on an empty database,
    which is why `connect` sets it before the schema and not after."""
    assert graph.execute("PRAGMA auto_vacuum").fetchone()[0] == 2  # INCREMENTAL

    with graph:
        graph.execute("INSERT INTO files(path, mtime, size, sha256) VALUES('a.py', 0, 1, 'x')")
        graph.executemany(
            "INSERT INTO meta(key, value) VALUES(?, ?)",
            [(f"k{i}", "v" * 4000) for i in range(400)],
        )
    # Checkpointed first: in WAL mode the pages are in the sidecar until then,
    # so an uncheckpointed `grown` reads as the empty file it started as.
    graph.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    grown = (tmp_path / "graph.db").stat().st_size
    with graph:
        graph.execute("DELETE FROM meta")
    store.reclaim(graph)
    assert (tmp_path / "graph.db").stat().st_size < grown


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
    Exercised through the pass's own two statements: the incremental delete this
    used to call had no caller outside this test.
    """
    _one_node(graph)
    assert graph.execute("SELECT count(*) c FROM nodes_fts").fetchone()["c"] == 1

    from graphrag import indexwrite

    graph.execute("DELETE FROM files")
    indexwrite.rebuild_fts(graph)

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


def test_the_two_closed_sets_have_a_reader():
    """Both sets carried a claim and nothing read them, so a name could drift.

    `EDGE_KINDS` is what `query.QUESTIONS` maps a question onto, and
    `NODE_KINDS` is what `queries.DEFINITION_KINDS` maps a capture onto. A name
    added on one side and not the other fails here rather than at a query.
    """
    from graphrag import queries, query

    asked = {kind for _, kinds, _ in query.QUESTIONS.values() for kind in kinds}
    assert asked <= store.EDGE_KINDS
    assert set(queries.DEFINITION_KINDS.values()) <= store.NODE_KINDS
