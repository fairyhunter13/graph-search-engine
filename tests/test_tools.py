"""The MCP surface: the four schemas, and the three error contracts.

`T-14` is the case the whole project exists for. A caller question against a
language with no call capture must name the gap. An empty list here reads as
"nothing calls this", and 18 of the 68 grammars with a tags file emit no call
capture at all.
"""

from __future__ import annotations

import asyncio

import pytest

from graphrag import cli, index, tools

CYCLE = {
    "a.py": "from b import beta\n\n\ndef alpha():\n    return beta()\n",
    "b.py": "def beta():\n    return 1\n",
}

# C has a tags file and no `@reference.call`, so it is the language the gap rule
# was written for. The body is never parsed for calls; only its presence matters.
NO_CALLS = {"main.c": "#include <stdio.h>\n\nint main(void) { return 0; }\n"}

# The four tools, and the arguments each one requires. The plan's Endpoints
# table is the source, so a rename there fails here rather than at a client.
REQUIRED = {
    "index": {"root"},
    "find_symbol": {"name", "root"},
    "neighbors": {"symbol", "root"},
    "blast_radius": {"symbol", "root"},
}


def _listed() -> dict:
    return {tool.name: tool for tool in asyncio.run(tools.mcp.list_tools())}


@pytest.fixture
def indexed(repo):
    root = repo("tools", CYCLE)
    index.index_once(root)
    return root


def test_tool_schemas_are_conformant():
    """`T-12`: four tools, each with a described input schema and a structured output."""
    listed = _listed()
    assert set(listed) == set(REQUIRED)
    for name, tool in listed.items():
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert set(schema.get("required", [])) == REQUIRED[name]
        assert tool.description and len(tool.description) > 40
        # Structured output is what lets a caller read `confidence` and
        # `evidence` as fields rather than parsing them out of prose.
        assert tool.output_schema is not None


def test_neighbors_carries_confidence(indexed):
    """`T-13`: every result names how sure the edge is and what resolved it."""
    answer = tools.neighbors(symbol="beta", root=str(indexed), question="callers")
    assert answer["results"], answer
    for row in answer["results"]:
        assert 0.0 < row["confidence"] <= 1.0
        assert row["evidence"] in ("same_file", "import", "package", "global", "scip")
    assert answer["capabilities"]["python"]


def test_missing_capability_is_reported(repo):
    """`T-14`: a language with no call capture names the gap, never an empty list."""
    root = repo("nocalls", NO_CALLS)
    index.index_once(root)
    answer = tools.neighbors(symbol="main", root=str(root), question="callers")
    assert answer["results"] == []
    assert any("c in this project" in gap for gap in answer["gaps"]), answer
    assert "calls" not in answer["capabilities"]["c"]


def test_unknown_argument_names_valid_set(indexed):
    """`T-15`: a bad question and a depth over the ceiling both name what is allowed."""
    bad = tools.neighbors(symbol="beta", root=str(indexed), question="who-eats-this")
    assert "who-eats-this" in bad["error"]
    assert "callers" in bad["error"]
    assert bad["results"] == []

    deep = tools.blast_radius(symbol="beta", root=str(indexed), depth=999)
    assert "999" in deep["error"] or "ceiling" in deep["error"]
    assert deep["results"] == []


def test_an_unindexed_root_names_the_index_tool(repo):
    """A project with no graph is not an empty graph, and the reply says which."""
    root = repo("unindexed", CYCLE)
    answer = tools.find_symbol(name="alpha", root=str(root))
    assert "index" in answer["error"]
    assert answer["results"] == []


def test_doctor_prints_the_capability_table(repo, capsys):
    """The command the plan's Integration section names, on a real project."""
    root = repo("doctor", NO_CALLS)
    index.index_once(root)
    assert cli.main(["doctor", str(root)]) == 0
    printed = capsys.readouterr().out
    assert '"c"' in printed
    assert "no call capture" in printed or "c in this project" in printed
