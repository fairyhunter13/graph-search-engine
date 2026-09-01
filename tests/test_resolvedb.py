"""The per-file facts, and the resolver that reads them at query time.

Every case here runs a real index pass over a real git repository. The point of
the redesign is that one file's rows are decided by one file, so a fixture that
stubbed the store would assert nothing about it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from graphrag import (
    config,
    dbread,
    discover,
    index,
    indexwrite,
    resolve,
    resolvedb,
    store,
    symtab,
)

REPO = Path(__file__).resolve().parents[1]

TREE = {
    "a.py": (
        "import os\n"
        "from b import thing as t\n"
        "\n"
        "\n"
        "class Holder:\n"
        "    def near(self):\n"
        "        return 1\n"
        "\n"
        "    def caller(self):\n"
        "        return self.near()\n"
        "\n"
        "\n"
        "def local():\n"
        "    return 2\n"
        "\n"
        "\n"
        "def f():\n"
        "    os.path.join('x')\n"
        "    local()\n"
        "    return t()\n"
    ),
    "b.py": "def thing():\n    return 3\n",
    "c.py": "from b import thing\n\n\ndef use():\n    return thing()\n",
}


@pytest.fixture
def tree(repo):
    root = repo("tree", TREE)
    index.index_once(root)
    conn = store.connect(config.index_path(root))
    yield root, conn
    conn.close()


def _refs(conn):
    return {r["name"]: r for r in conn.execute("SELECT * FROM refs")}


def test_a_reference_survives_a_pass_as_a_row(tree):
    """T-252. `receiver` and `is_member` are what narrows a candidate pool, and
    both were consumed into an edge and dropped before this."""
    _, conn = tree
    rows = _refs(conn)
    assert rows["join"]["receiver"] == "path"
    assert rows["join"]["is_member"] == 1
    assert rows["t"]["receiver"] == ""
    assert rows["t"]["is_member"] == 0
    assert rows["join"]["kind"] == "CALLS"
    assert rows["join"]["line"] > 0


def test_an_import_survives_a_pass_as_a_row(tree):
    """T-253. The module string is the one the source wrote, not a resolved one:
    module identity is still per-language and wrong in most of them."""
    _, conn = tree
    sql = "SELECT i.module, i.symbol, i.alias, i.line FROM imports i JOIN files f ON f.id = i.file_id WHERE f.path = 'a.py'"
    rows = {r["module"]: r for r in conn.execute(sql)}
    assert rows["os"]["symbol"] == ""
    assert rows["b"]["symbol"] == "thing"
    assert rows["b"]["alias"] == "t"
    assert rows["b"]["line"] == 2


def test_a_file_local_reference_is_an_edge_and_a_crossing_one_is_a_row(tree):
    """T-263. The split, asserted rather than trusted. A reference is written to
    exactly one of the two places, so no query counts it twice."""
    _, conn = tree
    rows = _refs(conn)
    assert "local" not in rows
    assert "near" not in rows
    assert set(rows) == {"join", "t", "thing"}

    stored = {
        (r["evidence"], r["name"])
        for r in conn.execute(
            "SELECT e.evidence, n.name FROM edges e JOIN nodes n ON n.id = e.dst "
            "WHERE e.kind = 'CALLS'"
        )
    }
    assert ("same_file", "local") in stored
    assert ("same_class", "near") in stored


def test_no_stored_edge_crosses_a_file(tree):
    """T-264 and T-279. The invariant itself, as an assertion over the store.

    `edges` cascades from `nodes` on `src` and on `dst`, so a stored cross-file
    edge is what makes a per-file delete unsafe. There must be none.
    """
    _, conn = tree
    crossing = conn.execute(
        "SELECT count(*) AS n FROM edges e "
        "JOIN nodes s ON s.id = e.src JOIN nodes d ON d.id = e.dst "
        "WHERE s.file_id != d.file_id"
    ).fetchone()["n"]
    assert crossing == 0


def test_the_enclosing_query_agrees_with_the_extractor(tree):
    """T-255. `refs` carries no `scope` column, and interval containment over
    columns already present is the substitute. The two must name the same node."""
    root, conn = tree
    ctx = dbread.Context(conn)
    for path, facts in index._facts(root, discover.enumerate_files(root)).items():
        file_id = conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()["id"]
        for ref in facts.references:
            found = ctx.enclosing(file_id, ref.call_site_byte)
            if ref.scope is None:
                assert found is None
                continue
            wanted = facts.definitions[ref.scope]
            row = conn.execute("SELECT start_byte FROM nodes WHERE id = ?", (found,)).fetchone()
            assert row["start_byte"] == wanted.start_byte


def test_a_name_the_other_file_defines_still_resolves(tree):
    """T-258. The staleness index-time resolution created: `c.py` calls `thing`
    and `b.py` defines it. No stored edge says so, and the answer is still exact."""
    _, conn = tree
    ctx = dbread.Context(conn)
    row = _refs(conn)["thing"]
    res = resolvedb.resolve_ref(ctx, dbread.row_to_ref(ctx, row))
    assert res.resolved
    assert res.candidates[0].symbol.path == "b.py"
    assert res.candidates[0].evidence == "import"


def test_a_wider_pool_is_ranked_and_never_forced(repo):
    """T-259. Two files define one name and neither is imported, so the answer is
    two candidates at the package tier. A forced single edge would be a guess."""
    root = repo(
        "wide",
        {
            "one.py": "def twin():\n    return 1\n",
            "two.py": "def twin():\n    return 2\n",
            "caller.py": "def go():\n    return twin()\n",
        },
    )
    index.index_once(root)
    conn = store.connect(config.index_path(root))
    try:
        ctx = dbread.Context(conn)
        rows = [r for r in conn.execute("SELECT * FROM refs WHERE name = 'twin'")]
        assert len(rows) == 1
        res = resolvedb.resolve_ref(ctx, dbread.row_to_ref(ctx, rows[0]))
        assert res.candidate_count == 2
        assert res.resolved is False
        assert {c.evidence for c in res.candidates} == {"package"}
    finally:
        conn.close()


def _table_answer(table, path, ref):
    """The candidate set `resolve.py` gives, keyed the way a node is keyed."""
    res = resolve.resolve_reference(table, path, ref)
    return {
        (c.symbol.path, table.files[c.symbol.path].definitions[c.symbol.index].start_byte)
        for c in res.candidates
    }


def test_the_two_resolvers_agree_over_this_repo(tmp_path):
    """T-254. The differential guard for the stage, over a real tree and not a
    fixture: this repo's own source, every reference in it.

    A same-file reference is an edge and a crossing one is a row, so the two
    halves are read from their own places and compared to the one answer the
    whole-tree resolver gives.
    """
    conn = store.connect(tmp_path / "diff.db")
    try:
        metas = discover.enumerate_files(REPO)
        facts = index._facts(REPO, metas)
        table = symtab.build({p: f for p, f in facts.items() if not f.error})

        with conn:
            file_ids = indexwrite.write_files(conn, metas, facts)
            nodes = indexwrite.write_nodes(conn, table, file_ids)
            decided: dict[str, list] = {}
            deferred: dict[str, list] = {}
            for path, file_facts in table.files.items():
                decided[path], deferred[path] = resolve.resolve_file_local(path, file_facts)
            indexwrite.write_refs(conn, deferred, file_ids)
            indexwrite.write_imports(conn, facts, file_ids)
            edges = indexwrite.structural_edges(table, nodes)
            for path, rows in decided.items():
                edges += indexwrite.reference_edges(path, rows, nodes)
            indexwrite.write_edges(conn, edges)

        # The decided half first. A same-file answer is stored, and it has to be
        # the answer the whole-tree resolver gives, or the split lost a caller.
        for path, rows in decided.items():
            for res in rows:
                wanted = _table_answer(table, path, res.reference)
                got = {
                    (
                        c.symbol.path,
                        table.files[c.symbol.path].definitions[c.symbol.index].start_byte,
                    )
                    for c in res.candidates
                }
                assert got == wanted, f"{path}:{res.reference.line} {res.reference.name}"

        ctx = dbread.Context(conn)
        checked = 0
        for row in conn.execute("SELECT * FROM refs"):
            ref = dbread.row_to_ref(ctx, row)
            source = next(
                r
                for r in table.files[ref.path].references
                if r.call_site_byte == ref.call_site_byte and r.name == ref.name
            )
            wanted = _table_answer(table, ref.path, source)
            got = {
                (c.symbol.path, c.symbol.start_byte)
                for c in resolvedb.resolve_ref(ctx, ref).candidates
            }
            assert got == wanted, f"{ref.path}:{ref.line} {ref.name}"
            checked += 1
        assert checked > 500
    finally:
        conn.close()
