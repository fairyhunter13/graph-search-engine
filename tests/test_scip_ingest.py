"""S-06. The overlay upgrades what tree-sitter found, and adds nothing.

Three rules carry the tier and each is graded here. A `kind` of 0 is five
indexers leaving the field alone, so it never overwrites. A SCIP occurrence is a
name mention until tree-sitter says a call happens at that byte. And a
relationship is the one fact no syntactic rule reaches.
"""

from __future__ import annotations

import scipwrite as w
from graphrag import config, index, store
from graphrag.scip import ingest

# Byte offsets computed by hand from the `\n` split. `Café` starts at line 4
# column 6, which is byte 34 under UTF-8 and column 10 at its UTF-16 end.
SRC = "def alpha():\n    return 1\n\n\nclass Café:\n    def beta(self):\n        return alpha()\n"
ALPHA = "scip-python python . . alpha()."
CAFE = "scip-python python . . `Café`#"
BETA = "scip-python python . . `Café`#beta()."

# `class Base` and `class Child(Base)`, each with a `run` method.
PAIR = (
    "class Base:\n    def run(self):\n        return 1\n\n\n"
    "class Child(Base):\n    def run(self):\n        return 2\n"
)
BASE = "scip-python python . . Base#"
CHILD = "scip-python python . . Child#"

DEFINITION = 1


def _store(repo, files):
    root = repo("proj", files)
    index.index_once(root)
    return root, store.connect(config.index_path(root), create=False)


def _document():
    """Every definition in `SRC`, so the coverage floors are cleared."""
    return w.document(
        "a.py",
        occurrences=[
            w.occurrence(ALPHA, roles=DEFINITION, span=(0, 4, 0, 9)),
            w.occurrence(CAFE, roles=DEFINITION, span=(4, 6, 4, 10)),
            w.occurrence(BETA, roles=DEFINITION, span=(5, 8, 5, 12)),
        ],
        symbols=[w.symbol_info(ALPHA, kind=26, documentation=["Adds one."])],
    )


def _node(conn, name):
    return conn.execute("SELECT * FROM nodes WHERE name = ?", (name,)).fetchone()


def test_a_definition_is_upgraded_and_its_kind_is_kept(repo, tmp_path):
    """T-104. `scip-python` sets no kind, so tree-sitter's survives untouched."""
    root, conn = _store(repo, {"a.py": SRC})
    path = tmp_path / "index.scip"
    w.write(path, "scip-python", [_document()])

    report = ingest.ingest(conn, path, root)
    assert report.nodes == 3

    got = _node(conn, "alpha")
    assert got["tier"] == "scip"
    assert got["qualified_name"] == ALPHA
    assert got["doc"] == "Adds one."
    # `kind` 26 is `Method` and this indexer never sets the field, so the 26 is
    # noise from the writer and the row keeps what the parse found.
    assert got["kind"] == "function"

    # The non-ASCII name is the offset table proving itself end to end: a
    # UTF-16 column of 10 has to reach the byte range tree-sitter recorded.
    assert _node(conn, "Café")["tier"] == "scip"
    conn.close()


def test_a_call_is_rewritten_only_where_tree_sitter_found_one(repo, tmp_path):
    """T-105. A name mention is not a call, and the intersection is the rule."""
    root, conn = _store(repo, {"a.py": SRC})
    path = tmp_path / "index.scip"
    call = w.occurrence(ALPHA, span=(6, 15, 6, 20))
    mention = w.occurrence(CAFE, span=(4, 6, 4, 10))
    document = w.document(
        "a.py",
        occurrences=[
            w.occurrence(ALPHA, roles=DEFINITION, span=(0, 4, 0, 9)),
            w.occurrence(CAFE, roles=DEFINITION, span=(4, 6, 4, 10)),
            w.occurrence(BETA, roles=DEFINITION, span=(5, 8, 5, 12)),
            call,
            mention,
        ],
    )
    w.write(path, "scip-python", [document])

    report = ingest.ingest(conn, path, root)
    assert report.calls == 1

    rows = conn.execute("SELECT * FROM edges WHERE evidence = 'scip'").fetchall()
    assert len(rows) == 1
    assert rows[0]["dst"] == _node(conn, "alpha")["id"]
    assert rows[0]["confidence"] == 1.0
    assert rows[0]["resolved"] == 1
    assert rows[0]["producer"] == "scip-python"

    # The mention sits on a definition byte and not a call span, so it buys no
    # edge. Without this the tier would invent calls out of every reference.
    assert (
        conn.execute("SELECT count(*) AS n FROM edges WHERE call_site_byte = 34").fetchone()["n"]
        == 0
    )
    conn.close()


def test_an_implementation_relationship_becomes_an_edge(repo, tmp_path):
    """T-106. The tier's highest-value output, and no syntactic substitute exists."""
    root, conn = _store(repo, {"a.py": PAIR})
    path = tmp_path / "index.scip"
    document = w.document(
        "a.py",
        occurrences=[
            w.occurrence(BASE, roles=DEFINITION, span=(0, 6, 0, 10)),
            w.occurrence(CHILD, roles=DEFINITION, span=(5, 6, 5, 11)),
        ],
        symbols=[
            w.symbol_info(BASE),
            w.symbol_info(CHILD, relationships=[w.relationship(BASE, implementation=True)]),
        ],
    )
    w.write(path, "scip-python", [document])

    report = ingest.ingest(conn, path, root)
    assert report.implements == 1

    row = conn.execute("SELECT * FROM edges WHERE kind = 'IMPLEMENTS'").fetchone()
    assert row["src"] == _node(conn, "Child")["id"]
    assert row["dst"] == _node(conn, "Base")["id"]
    assert row["evidence"] == "scip"
    conn.close()


def test_a_second_ingest_replaces_its_own_implements_edges(repo, tmp_path):
    """T-125. The overlay is re-run on every re-index, so it has to be idempotent.

    A call edge is keyed by its call site byte and replaces itself. An implements
    edge is keyed by nothing, so the second run doubled every one of them and the
    graph reported one interface twice.
    """
    root, conn = _store(repo, {"a.py": PAIR})
    path = tmp_path / "index.scip"
    document = w.document(
        "a.py",
        occurrences=[
            w.occurrence(BASE, roles=DEFINITION, span=(0, 6, 0, 10)),
            w.occurrence(CHILD, roles=DEFINITION, span=(5, 6, 5, 11)),
        ],
        symbols=[
            w.symbol_info(BASE),
            w.symbol_info(CHILD, relationships=[w.relationship(BASE, implementation=True)]),
        ],
    )
    w.write(path, "scip-python", [document])

    assert ingest.ingest(conn, path, root).implements == 1
    assert ingest.ingest(conn, path, root).implements == 1
    rows = conn.execute("SELECT * FROM edges WHERE kind = 'IMPLEMENTS'").fetchall()
    assert len(rows) == 1
    assert rows[0]["producer"] == "scip-python"
    conn.close()


def test_a_relationship_that_is_not_an_implementation_is_ignored(repo, tmp_path):
    """The field is one flag among four, so a reference relationship earns nothing."""
    root, conn = _store(repo, {"a.py": PAIR})
    path = tmp_path / "index.scip"
    document = w.document(
        "a.py",
        occurrences=[
            w.occurrence(BASE, roles=DEFINITION, span=(0, 6, 0, 10)),
            w.occurrence(CHILD, roles=DEFINITION, span=(5, 6, 5, 11)),
        ],
        symbols=[w.symbol_info(CHILD, relationships=[w.relationship(BASE)])],
    )
    w.write(path, "scip-python", [document])
    assert ingest.ingest(conn, path, root).implements == 0
    conn.close()


# Two files define `alpha` and a third calls it with no import, so the ranked
# tier reaches the repo-global rule and emits both candidates unresolved.
AMBIGUOUS = {
    "a.py": "def alpha():\n    return 1\n",
    "b.py": "def alpha():\n    return 2\n",
    "c.py": "def gamma():\n    return alpha()\n",
}
ALPHA_A = "scip-python python . . `a`/alpha()."
ALPHA_B = "scip-python python . . `b`/alpha()."
GAMMA = "scip-python python . . `c`/gamma()."


def test_the_tier_raises_the_resolved_share_and_agrees_with_the_parse(repo, tmp_path):
    """The claim the whole overlay rests on, measured with the tier off and on.

    An assertion that the tier ingests something is not the claim. The claim is
    that resolved edges rise, and that the edge SCIP resolves names a file the
    parse already held as a candidate. A target the parse never saw would mean
    the overlay is extracting rather than upgrading.
    """
    root, conn = _store(repo, AMBIGUOUS)

    def resolved():
        row = conn.execute(
            "SELECT count(*) AS n FROM edges WHERE kind = 'CALLS' AND resolved = 1"
        ).fetchone()
        return row["n"]

    candidates = conn.execute(
        "SELECT f.path AS path FROM edges e"
        " JOIN nodes n ON n.id = e.dst JOIN files f ON f.id = n.file_id"
        " WHERE e.kind = 'CALLS' AND n.name = 'alpha'"
    ).fetchall()
    assert {row["path"] for row in candidates} == {"a.py", "b.py"}
    before = resolved()
    assert before == 0

    path = tmp_path / "index.scip"
    w.write(
        path,
        "scip-python",
        [
            w.document(
                "a.py", occurrences=[w.occurrence(ALPHA_A, roles=DEFINITION, span=(0, 4, 0, 9))]
            ),
            w.document(
                "b.py", occurrences=[w.occurrence(ALPHA_B, roles=DEFINITION, span=(0, 4, 0, 9))]
            ),
            w.document(
                "c.py",
                occurrences=[
                    w.occurrence(GAMMA, roles=DEFINITION, span=(0, 4, 0, 9)),
                    w.occurrence(ALPHA_A, span=(1, 11, 1, 16)),
                ],
            ),
        ],
    )
    assert ingest.ingest(conn, path, root).calls == 1

    assert resolved() > before
    upgraded = conn.execute(
        "SELECT f.path AS path, e.confidence AS confidence FROM edges e"
        " JOIN nodes n ON n.id = e.dst JOIN files f ON f.id = n.file_id"
        " WHERE e.evidence = 'scip'"
    ).fetchall()
    assert len(upgraded) == 1
    assert upgraded[0]["confidence"] == 1.0
    # The parse held this file as one of its two candidates, so the tier chose
    # between them rather than naming a target of its own.
    assert upgraded[0]["path"] == "a.py"
    conn.close()


def test_a_definition_at_a_byte_no_node_holds_is_dropped(repo, tmp_path):
    """SCIP finds names tree-sitter does not, and the tier never creates a node."""
    root, conn = _store(repo, {"a.py": SRC})
    path = tmp_path / "index.scip"
    document = w.document(
        "a.py",
        occurrences=[
            w.occurrence(ALPHA, roles=DEFINITION, span=(0, 4, 0, 9)),
            w.occurrence(CAFE, roles=DEFINITION, span=(4, 6, 4, 10)),
            w.occurrence(BETA, roles=DEFINITION, span=(5, 8, 5, 12)),
            # A local variable on the return line. No node carries that range.
            w.occurrence("scip-python python . . total.", roles=DEFINITION, span=(1, 11, 1, 12)),
        ],
    )
    w.write(path, "scip-python", [document])
    before = conn.execute("SELECT count(*) AS n FROM nodes").fetchone()["n"]
    assert ingest.ingest(conn, path, root).nodes == 3
    assert conn.execute("SELECT count(*) AS n FROM nodes").fetchone()["n"] == before
    conn.close()
