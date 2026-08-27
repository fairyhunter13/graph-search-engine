"""S-06. The coverage guard, which is the only thing that reads a collapsed run.

`scip-python` never sets `autoSearchPaths`, so on a `src/` layout it drops every
cross-package reference, and `safe_analyze` drops a file it could not analyse.
Both paths exit 0 and both write an index. Counting that index against the
tree-sitter census is what tells one of those runs from a working one.
"""

from __future__ import annotations

import pytest

import scipwrite as w
from graphrag import config, index, store
from graphrag.scip import ingest

ALPHA = "def alpha():\n    return 1\n"
BETA = "def beta():\n    return 2\n"
GAMMA = "def gamma():\n    return 3\n"


def _store(repo, files):
    root = repo("proj", files)
    index.index_once(root)
    return root, store.connect(config.index_path(root), create=False)


def _defined(name, line_length):
    """One definition occurrence for a `def <name>():` on line 0."""
    return w.occurrence(f"scip-python python . . {name}().", roles=1, span=(0, 4, 0, line_length))


def test_collapsed_index_is_refused(repo, tmp_path):
    """T-19. Two of three files missing is a refusal, and it writes nothing."""
    root, conn = _store(repo, {"a.py": ALPHA, "b.py": BETA, "c.py": GAMMA})
    path = tmp_path / "index.scip"
    w.write(path, "scip-python", [w.document("a.py", occurrences=[_defined("alpha", 9)])])

    before = conn.execute("SELECT count(*) AS n FROM nodes WHERE tier = 'scip'").fetchone()["n"]
    with pytest.raises(ingest.CoverageError) as caught:
        ingest.ingest(conn, path, root)

    reason = str(caught.value)
    assert "1 of 3 files" in reason
    assert "33%" in reason and "60%" in reason

    # The refusal runs before any write, so a bad index costs the project
    # nothing. A partial overlay is worse than none, because it reads as resolved.
    after = conn.execute("SELECT count(*) AS n FROM nodes WHERE tier = 'scip'").fetchone()["n"]
    assert before == after == 0
    conn.close()


def test_a_full_index_with_no_definitions_is_refused_too(repo, tmp_path):
    """Every file present and no symbol found is the `safe_analyze` shape."""
    root, conn = _store(repo, {"a.py": ALPHA, "b.py": BETA})
    path = tmp_path / "index.scip"
    w.write(
        path,
        "scip-python",
        [w.document("a.py"), w.document("b.py")],
    )
    with pytest.raises(ingest.CoverageError) as caught:
        ingest.ingest(conn, path, root)
    assert "defines 0 symbols" in str(caught.value)
    conn.close()


def test_a_language_this_project_does_not_hold_is_refused_by_name(repo, tmp_path):
    """No census means no floor to measure against, so the reason says so."""
    root, conn = _store(repo, {"a.py": ALPHA})
    path = tmp_path / "index.scip"
    w.write(path, "scip-go", [w.document("a.py")])
    with pytest.raises(ingest.CoverageError) as caught:
        ingest.ingest(conn, path, root)
    assert "no file in this project is a language scip-go indexes" in str(caught.value)
    conn.close()


def test_the_guard_reads_and_never_writes(repo, tmp_path):
    """`coverage` is the half that runs first, so it takes no transaction."""
    _root, conn = _store(repo, {"a.py": ALPHA, "b.py": BETA})
    path = tmp_path / "index.scip"
    w.write(path, "scip-python", [w.document("a.py", occurrences=[_defined("alpha", 9)])])
    got = ingest.coverage(conn, path, "scip-python", ("python",))
    assert got.documents == 1
    assert got.matched == 1
    assert got.census_files == 2
    assert got.file_share == 0.5
    assert ingest.check(got)
    conn.close()
