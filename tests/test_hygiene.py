"""The public-hygiene gate, and the ceilings that keep the layout true.

`GRAPHRAG_NAME_BAN` is unset by default, and unset is the *failing* state. A
check that silently does nothing when a variable is missing is a check that
passed on every machine that never set it. A clean clone declares itself with
`GRAPHRAG_NAME_BAN=none`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from graphrag import config

SRC = Path(__file__).resolve().parent.parent / "src" / "graphrag"
MODULE_LINE_CEILING = 300


def _modules() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_every_module_is_under_the_line_ceiling():
    """A module over the ceiling is doing two jobs, and the seam is the fix."""
    over = {
        path.relative_to(SRC).as_posix(): len(path.read_text().splitlines())
        for path in _modules()
        if len(path.read_text().splitlines()) > MODULE_LINE_CEILING
    }
    assert over == {}


def test_scip_is_the_only_subpackage():
    """Flat by design. A second subpackage needs the argument `scip/` makes."""
    packages = {p.parent.name for p in SRC.rglob("__init__.py")} - {"graphrag"}
    assert packages <= {"scip"}


def test_config_imports_no_sibling():
    """Everything depends on `config`, so a cycle through it is unresolvable."""
    text = (SRC / "config.py").read_text()
    assert not re.search(r"^from \.\w* import|^from \. import", text, re.MULTILINE)


def test_no_module_carries_a_home_path():
    """A literal home path ships one machine's layout to every other one."""
    pattern = re.compile(r"[\"']/home/|[\"']/Users/")
    offenders = [p.relative_to(SRC).as_posix() for p in _modules() if pattern.search(p.read_text())]
    assert offenders == []


def _banned(raw: str) -> list[str]:
    """`none` is a declaration, and it is the only word that empties the list."""
    if raw.strip() == "none":
        return []
    return [n.strip() for n in raw.split(",") if n.strip()]


def test_the_name_ban_fails_closed_when_it_is_unset():
    """Unset is the failing state, so the gate cannot pass by not running."""
    if not config.NAME_BAN.strip():
        pytest.fail(
            "GRAPHRAG_NAME_BAN is unset. Set it to a comma-separated list of names "
            "that must not appear in shipped source, or to `none` to declare a "
            "clean clone. Unset is not the same as none."
        )
    found = {
        p.relative_to(SRC).as_posix(): name
        for p in _modules()
        for name in _banned(config.NAME_BAN)
        if name in p.read_text()
    }
    assert found == {}


def test_a_banned_name_in_a_module_is_caught():
    """The other half. A ban nobody has seen reject is not a gate."""
    assert _banned("none") == []
    assert _banned("acme, widgets") == ["acme", "widgets"]
    hits = [p for p in _modules() for name in _banned("graphrag") if name in p.read_text()]
    assert hits, "the ban matches nothing, so it proves nothing"
