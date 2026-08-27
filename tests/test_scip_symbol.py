"""S-06. The symbol string, which is the only name SCIP carries.

A SCIP symbol is five space-separated fields and a descriptor tail, and the tail
is where the name lives. Its separators are also legal inside a backtick-quoted
name, so the parse is a walk and never a split.
"""

from __future__ import annotations

from graphrag.scip import symbol

PYTHON = "scip-python python . . pkg/mod/`Café`#meth()."


def test_the_descriptor_tail_carries_the_kind_of_each_step():
    got = symbol.descriptors(PYTHON)
    assert [(d.name, d.kind) for d in got] == [
        ("pkg", "module"),
        ("mod", "module"),
        ("Café", "class"),
        ("meth", "method"),
    ]
    assert symbol.name(PYTHON) == "meth"


def test_a_backtick_quoted_name_keeps_its_separators():
    """A space and a dot inside a quoted name are not field boundaries."""
    got = symbol.descriptors("scip-java java . . `a b`/`c.d`#")
    assert [d.name for d in got] == ["a b", "c.d"]


def test_a_local_symbol_names_nothing_outside_its_document():
    """`local 4` is document-scoped, so it can never be a cross-file target."""
    assert symbol.is_local("local 4") is True
    assert symbol.is_local(PYTHON) is False
    assert symbol.descriptors("local 4") == []


def test_a_parameter_group_is_no_part_of_the_name():
    """`meth().` and `meth(x).` are one method, and the group is the overload."""
    assert symbol.name("scip-go go . . pkg/Do(int).") == "Do"
    assert symbol.name("scip-java java . . pkg/C#do(+1).") == "do"


def test_an_unset_kind_keeps_whatever_tree_sitter_found():
    """Five of the ten live indexers leave the field 0, so 0 is the common case."""
    assert symbol.kind_of(0) == ""
    assert symbol.kind_of(999) == ""
    assert symbol.kind_of(7) == "class"
    assert symbol.kind_of(26) == "method"
