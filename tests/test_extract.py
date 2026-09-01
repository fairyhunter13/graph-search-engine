"""Golden symbol counts for the wave-one languages, on real parses.

A golden is a count taken from a fixture that is read here and nowhere else, so
a change in the pin or in the capture mapping moves a number rather than passing
quietly with less data.
"""

from __future__ import annotations

import collections
from pathlib import Path

import pytest

from graphrag import extract

FIXTURES = Path(__file__).parent / "fixtures" / "wave1"


def _facts(name: str, lang: str):
    return extract.extract(lang, (FIXTURES / name).read_text(encoding="utf-8"))


def _kinds(rows) -> dict[str, int]:
    return dict(collections.Counter(r.kind for r in rows))


def test_python_golden_symbol_counts():
    facts = _facts("orders.py", "python")
    assert facts.error == ""
    assert _kinds(facts.definitions) == {"class": 2, "method": 4, "function": 2}
    assert sorted(d.qualified_name for d in facts.definitions) == [
        "Order",
        "Order.__init__",
        "Order.subtotal",
        "Order.tax",
        "RushOrder",
        "RushOrder.tax",
        "load",
        "retry",
    ]
    assert _kinds(facts.references) == {"CALLS": 11}
    assert [(i.module, i.symbol, i.alias) for i in facts.imports] == [
        ("logging", "", ""),
        ("os.path", "", "path"),
        ("decimal", "Decimal", ""),
        (".rates", "TAXES", ""),
        (".rates", "convert", ""),
    ]


def test_a_method_is_recovered_from_containment():
    """Python's tags file emits no `@definition.method`, so the parent decides."""
    facts = _facts("orders.py", "python")
    by_name = {d.qualified_name: d for d in facts.definitions}
    assert by_name["Order.subtotal"].kind == "method"
    assert by_name["load"].kind == "function"
    assert by_name["Order.tax"].parent == by_name["Order.tax"].parent
    assert facts.definitions[by_name["Order.tax"].parent].name == "Order"


def test_a_call_scope_is_the_enclosing_definition():
    facts = _facts("orders.py", "python")
    calls = {r.name: r for r in facts.references}
    scope = facts.definitions[calls["convert"].scope]
    assert scope.qualified_name == "RushOrder.tax"
    assert calls["subtotal"].is_member is True
    assert calls["sum"].is_member is False


def test_typescript_golden_symbol_counts():
    facts = _facts("orders.ts", "typescript")
    assert facts.error == ""
    assert _kinds(facts.definitions) == {"class": 1, "method": 2, "function": 1}
    assert _kinds(facts.references) == {"CALLS": 3, "REFERENCES": 4}
    assert [(i.module, i.symbol, i.alias) for i in facts.imports] == [
        ("./money", "Money", ""),
        ("./rates", "TAXES", ""),
        ("./rates", "convert", ""),
        ("./log", "", "log"),
    ]


def test_php_golden_symbol_counts():
    facts = _facts("Orders.php", "php")
    assert facts.error == ""
    assert _kinds(facts.definitions) == {"class": 3, "method": 2, "function": 1}
    assert _kinds(facts.references) == {"CALLS": 3, "IMPLEMENTS": 1, "REFERENCES": 3}
    assert [(i.module, i.symbol, i.alias) for i in facts.imports] == [
        ("App\\Models\\User", "", ""),
        ("App\\Support\\Money", "", "M"),
    ]


def test_a_php_static_call_needs_the_repair_layer():
    """`User::find` is the dominant call shape, and the pack's query misses it."""
    facts = _facts("Orders.php", "php")
    calls = {r.name for r in facts.references if r.kind == "CALLS"}
    assert {"find", "zero"} <= calls

    impls = {r.name for r in facts.references if r.kind == "IMPLEMENTS"}
    assert impls == {"Auditable"}


def test_one_import_row_per_statement():
    """A general pattern matches what the specific ones match, and that is one row."""
    for name, lang in (("orders.ts", "typescript"), ("Orders.php", "php")):
        facts = _facts(name, lang)
        modules = [i.module for i in facts.imports if not i.symbol and not i.alias]
        assert len(modules) == len(set(modules))
        for row in facts.imports:
            if row.symbol or row.alias:
                assert all(
                    other.symbol or other.alias
                    for other in facts.imports
                    if other.module == row.module
                )


def test_an_unknown_language_is_reported_and_not_raised():
    facts = extract.extract("not-a-language", "x = 1\n")
    assert facts.error == "no parser for not-a-language"
    assert facts.reason == "no_parser"
    assert facts.definitions == []


def test_a_query_that_raises_leaves_the_file_saying_so(monkeypatch):
    """`T-301`. Cause F had no signal at all before this.

    `_run` swallows a query error and returns `[]`, which is byte-identical in the
    store to a file that parsed clean and defined nothing. A language with the
    full capability set reaching `tier='none'` is the one shape that cannot be
    read off the tier, so the mark is the whole point.
    """

    def boom(*_args):
        raise RuntimeError("query is broken")

    monkeypatch.setattr(extract, "_compiled", boom)
    facts = extract.extract("python", "def alpha():\n    return 1\n")
    assert facts.reason == "query_failed"
    assert facts.error == ""
    assert facts.definitions == []


@pytest.mark.parametrize("name,lang", [("orders.py", "python"), ("orders.ts", "typescript")])
def test_every_definition_carries_a_line_range(name, lang):
    for d in _facts(name, lang).definitions:
        assert 1 <= d.start_line <= d.end_line
        assert d.start_byte < d.end_byte <= d.body_end_byte
