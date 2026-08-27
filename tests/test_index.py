"""The index pass, the queue, and traversal over a real import cycle.

`T-09` is the cycle: three modules that import each other, asserting a bounded
walk terminates and counts each dependent once. No mocks, so the cycle is a real
git repo the extractor parses.
"""

from __future__ import annotations

import pytest

from graphrag import config, index, query, registry, store, traverse

CYCLE = {
    "a.py": ("from b import beta\n\n\ndef alpha():\n    return beta()\n"),
    "b.py": ("from c import gamma\n\n\ndef beta():\n    return gamma()\n"),
    "c.py": ("import a\n\n\ndef gamma():\n    return a.alpha()\n"),
}


@pytest.fixture
def cycle(repo):
    root = repo("cycle", CYCLE)
    report = index.index_once(root)
    conn = store.connect(config.index_path(root))
    yield root, report, conn
    conn.close()


def test_a_pass_writes_nodes_and_edges(cycle):
    _, report, conn = cycle
    assert report.files == 3
    assert report.parsed == 3
    assert report.errors == {}
    assert report.languages == {"python": 3}
    assert report.nodes >= 6  # three modules, three functions
    assert report.edges > 0
    assert store.counts(conn)["resolved"] > 0


def test_an_unchanged_tree_is_not_reparsed(cycle):
    root, _, _ = cycle
    again = index.index_once(root)
    assert again.unchanged is True
    assert again.parsed == 0


def test_a_changed_file_makes_the_pass_run(cycle):
    root, _, _ = cycle
    (root / "a.py").write_text(CYCLE["a.py"] + "\n\ndef delta():\n    return alpha()\n")
    again = index.index_once(root)
    assert again.unchanged is False
    assert again.parsed == 3


def test_callers_of_a_function_in_the_cycle(cycle):
    _, _, conn = cycle
    answer = query.neighbors(conn, "gamma", question="callers")
    assert [r.name for r in answer.results] == ["beta"]
    assert answer.results[0].path == "b.py"


def test_blast_radius_terminates_over_the_cycle(cycle):
    """The whole of `T-09`: bounded, terminating, and each node once."""
    _, _, conn = cycle
    answer = query.blast_radius(conn, "gamma", depth=config.MAX_DEPTH)
    ids = [r.node_id for r in answer.results]
    assert ids
    assert len(ids) == len(set(ids))
    assert max(r.depth for r in answer.results) <= config.MAX_DEPTH


def test_a_depth_over_the_ceiling_is_refused(cycle):
    _, _, conn = cycle
    with pytest.raises(ValueError, match="ceiling"):
        query.blast_radius(conn, "gamma", depth=config.MAX_DEPTH + 1)


def test_an_unknown_question_names_the_valid_set(cycle):
    _, _, conn = cycle
    with pytest.raises(ValueError, match="callers"):
        query.neighbors(conn, "gamma", question="callrs")


def test_an_unknown_symbol_is_a_gap_and_not_an_empty_list(cycle):
    _, _, conn = cycle
    answer = query.neighbors(conn, "no_such_name", question="callers")
    assert answer.results == []
    assert "no_such_name" in answer.gaps[0]


def test_an_unknown_direction_is_refused():
    with pytest.raises(ValueError, match="upstream"):
        traverse._columns("sideways")


def test_the_queue_drops_a_queued_job_and_requeues_a_running_one(tmp_path):
    queue = index.Queue()
    assert queue.submit(tmp_path) == "queued"
    assert queue.submit(tmp_path) == "dropped"

    taken = queue.take(timeout=0.1)
    assert taken == str(tmp_path.resolve())
    assert queue.submit(tmp_path) == "requeued"

    queue.done(taken)
    assert queue.take(timeout=0.1) == taken
    assert queue.take(timeout=0.1) is None


def test_find_symbol_returns_a_location_and_never_a_body(cycle):
    _, _, conn = cycle
    hits = query.find_symbol(conn, "alpha")
    assert [h.path for h in hits] == ["a.py"]
    assert hits[0].kind == "function"
    assert hits[0].line > 0
    assert not hasattr(hits[0], "body")


def test_the_capability_report_names_every_language_in_the_project(cycle):
    _, _, conn = cycle
    report = query.capability_report(conn)
    assert set(report) == {"python"}
    assert "calls" in report["python"]


def test_the_registry_row_carries_the_figures_the_reach_hook_reads(cycle):
    """T-90. The hook reads the row and never the store.

    `graphRegistryRow` in ccw unmarshals `node_count`, `edge_count`,
    `resolved_edge_count` and `capabilities`. A row without them reports an
    indexed project as an empty graph, which is the absence this engine
    refuses to return.
    """
    root, report, _ = cycle
    registry.claim(root, direct=True)
    index.record(report)
    row = registry.get(root).to_json()
    assert row["node_count"] == report.nodes > 0
    assert row["edge_count"] == report.edges > 0
    assert row["resolved_edge_count"] == report.resolved > 0
    assert "calls" in row["capabilities"]["python"]

    # An unchanged pass writes no graph, so the row keeps what the last real
    # pass left. Zeroing here would report a live graph as empty.
    index.record(index.index_once(root))
    kept = registry.get(root).to_json()
    assert kept["node_count"] == row["node_count"]
    assert kept["capabilities"] == row["capabilities"]
