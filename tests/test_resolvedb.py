"""The per-file facts, and the resolver that reads them at query time.

Every case here runs a real index pass over a real git repository. The point of
the redesign is that one file's rows are decided by one file, so a fixture that
stubbed the store would assert nothing about it.
"""

from __future__ import annotations

import pytest

from graphrag import config, index, store

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
}


@pytest.fixture
def tree(repo):
    root = repo("tree", TREE)
    index.index_once(root)
    conn = store.connect(config.index_path(root))
    yield root, conn
    conn.close()


def test_a_reference_survives_a_pass_as_a_row(tree):
    """T-252. `receiver` and `is_member` are what narrows a candidate pool, and
    both were consumed into an edge and dropped before this."""
    _, conn = tree
    rows = {
        r["name"]: r for r in conn.execute("SELECT name, kind, receiver, is_member, line FROM refs")
    }
    assert rows["join"]["receiver"] == "path"
    assert rows["join"]["is_member"] == 1
    assert rows["local"]["receiver"] == ""
    assert rows["local"]["is_member"] == 0
    assert rows["join"]["kind"] == "CALLS"
    assert rows["join"]["line"] > 0


def test_an_import_survives_a_pass_as_a_row(tree):
    """T-253. The module string is the one the source wrote, not a resolved one:
    module identity is still per-language and wrong in most of them."""
    _, conn = tree
    rows = {r["module"]: r for r in conn.execute("SELECT module, symbol, alias, line FROM imports")}
    assert rows["os"]["symbol"] == ""
    assert rows["b"]["symbol"] == "thing"
    assert rows["b"]["alias"] == "t"
    assert rows["b"]["line"] == 2
