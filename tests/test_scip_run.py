"""S-06. The tier's outer edge: the capability table, and refusal as an outcome.

One collapsed index must not cost the project the graph tree-sitter already
built, so `overlay` reports a refusal in the same shape as a success. An
operator reads which tool was refused and by how much, from the same line.
"""

from __future__ import annotations

import pytest

import scipwrite as w
from graphrag import config, index, scip, store
from graphrag.scip import run

SRC = "def alpha():\n    return 1\n"
ALPHA = "scip-python python . . alpha()."


def _store(repo, files):
    root = repo("proj", files)
    index.index_once(root)
    return root, store.connect(config.index_path(root), create=False)


def test_the_capability_table_is_per_indexer_and_never_per_language():
    """`kind` and relationships are capabilities, exactly like a tags capture."""
    assert run.indexer("scip-python").sets_kind is False
    assert run.indexer("scip-go").sets_kind is True
    # rust-analyzer builds `relationships: Vec::new()`, so Rust trait impls come
    # from tree-sitter or from nowhere.
    assert run.indexer("rust-analyzer").emits_relationships is False
    assert [i.name for i in run.for_language("python")] == ["scip-python"]
    assert run.for_language("cobol") == []


def test_an_unknown_indexer_is_an_error_that_names_the_known_ones():
    with pytest.raises(run.RunError) as caught:
        run.indexer("scip-cobol")
    assert "scip-python" in str(caught.value)


def test_a_refusal_is_an_outcome_and_never_an_exception(repo, tmp_path):
    """T-107. A bad index costs the project nothing, and the line says why."""
    root, conn = _store(repo, {"a.py": SRC, "b.py": SRC.replace("alpha", "beta")})
    w.write(
        root / run.OUTPUT_NAME,
        "scip-python",
        [w.document("a.py", occurrences=[w.occurrence(ALPHA, roles=1, span=(0, 4, 0, 9))])],
    )

    got = scip.overlay(conn, root, ["scip-python", "scip-go"])
    assert set(got) == {"scip-python", "scip-go"}
    assert got["scip-python"].startswith("refused: ")
    assert "1 of 2 files" in got["scip-python"]

    # The index at the root was written by another tool, so the second indexer
    # is refused by name rather than reading a file it did not produce.
    assert "was not written by scip-go" in got["scip-go"]
    conn.close()


def test_the_overlay_is_off_unless_the_project_asks():
    """Two switches, and the environment can only ever subtract."""
    assert scip.enabled(False) is False
    assert scip.enabled(True) is True


def test_the_index_pass_runs_the_overlay_only_where_the_config_asks(repo, tmp_path):
    """T-108. The tier is deletable in one move, so the import is lazy too."""
    files = {"a.py": SRC, "b.py": SRC.replace("alpha", "beta")}
    root = repo("proj", files)
    assert index.index_once(root).scip == {}

    (root / ".graphrag.yaml").write_text("scip: true\nscip_indexers: [scip-python]\n")
    w.write(
        root / run.OUTPUT_NAME,
        "scip-python",
        [
            w.document("a.py", occurrences=[w.occurrence(ALPHA, roles=1, span=(0, 4, 0, 9))]),
            w.document(
                "b.py",
                occurrences=[
                    w.occurrence(ALPHA.replace("alpha", "beta"), roles=1, span=(0, 4, 0, 8))
                ],
            ),
        ],
    )
    got = index.index_once(root, force=True).scip
    assert got["scip-python"] == "2 nodes, 0 calls, 0 implementations"


def test_an_index_that_is_not_there_is_refused_rather_than_invented(repo):
    """No file and no runnable tool is a refusal naming the path it wanted."""
    root, conn = _store(repo, {"a.py": SRC})
    got = scip.overlay(conn, root, ["scip-java"])
    assert got["scip-java"].startswith("refused: no SCIP index at ")
    conn.close()


def test_an_empty_index_is_not_a_scip_index(repo):
    """A zero-byte file parses as an index with no documents, so it is refused."""
    root, conn = _store(repo, {"a.py": SRC})
    (root / run.OUTPUT_NAME).write_bytes(b"")
    got = scip.overlay(conn, root, ["scip-java"])
    assert "is not a SCIP index" in got["scip-java"]
    conn.close()
