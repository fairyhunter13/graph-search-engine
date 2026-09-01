"""The plan pair, graded. `docs/test-plan.md` described five checks that no gate ran.

`.githooks/pre-push` dropped the plan-pair block on 2026-08-29 and both documents
kept describing it. Six `done` rows outlived the tests behind them, three `Paths
it owns` entries outlived their files, and nineteen tests were written that no
row names. Every one of those is what an unrun gate leaves behind.

Collection is an AST walk over `tests/test_*.py` and not `pytest --collect-only`.
A pytest run inside a pytest run costs a subprocess and a second import of the
whole suite, and the column holds no parametrised id -- 0 of 303 rows carry a
`[case]` suffix -- so real collection would name nothing the AST does not.

A `(ccw)` prefix marks a node or a path in the sibling repository. It is exempt
and it is counted, because an escape hatch nobody can see the size of is a hole.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEST_PLAN = REPO / "docs" / "test-plan.md"
DEV_PLAN = REPO / "docs" / "development-plan.md"
FOREIGN = "("

# `| ID | Title | S-nn | D-nn covered | Status | Test node ID |`
_TEST_ROW = re.compile(r"^\|\s*(T-\d+)\s*\|")
# `| ID | Title | Status | Paths it owns | T-nn covering it |`
_DEV_ROW = re.compile(r"^\|\s*(D-\d+)\s*\|")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _rows(path: Path, pattern: re.Pattern[str]) -> list[list[str]]:
    return [
        _cells(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if pattern.match(line)
    ]


def _test_rows() -> list[list[str]]:
    return _rows(TEST_PLAN, _TEST_ROW)


def _dev_rows() -> list[list[str]]:
    return _rows(DEV_PLAN, _DEV_ROW)


def _listed(cell: str) -> list[str]:
    """One cell holding a comma-separated list. A row may name two nodes."""
    return [part.strip() for part in cell.split(",") if part.strip()]


def _defined() -> set[str]:
    """Every `test_*` function defined under `tests/`, as a pytest node id."""
    out = set()
    for path in sorted((REPO / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(REPO).as_posix()
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
                "test_"
            ):
                out.add(f"{rel}::{node.name}")
            elif isinstance(node, ast.ClassDef):
                out.update(
                    f"{rel}::{node.name}::{child.name}"
                    for child in node.body
                    if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
                    and child.name.startswith("test_")
                )
    return out


def _tracked() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return {name for name in out.stdout.split("\0") if name}


def test_every_done_row_names_a_test_that_exists():
    """`T-307`. The drift that rotted six rows, in the direction it rotted."""
    rows = _test_rows()
    assert len(rows) > 300, "the table did not parse"
    defined = _defined()
    missing = [
        f"{row[0]} names {node}"
        for row in rows
        if row[4] == "done"
        for node in _listed(row[5])
        if not node.startswith(FOREIGN) and node not in defined
    ]
    assert missing == []


def test_a_foreign_node_is_exempt_and_the_exemption_is_visible():
    """`T-308`. An escape hatch nobody can size is a hole, so its size is asserted."""
    exempt = [node for row in _test_rows() for node in _listed(row[5]) if node.startswith(FOREIGN)]
    assert exempt, "no row is exempt, so the exemption is untested and can rot unseen"
    assert all(node.startswith("(ccw) ") for node in exempt)


def test_a_row_with_no_node_is_planned():
    """A `done` row that names nothing resolves nothing, and no arm would see it."""
    silent = [row[0] for row in _test_rows() if not row[5] and row[4] != "planned"]
    assert silent == []


def test_every_test_that_exists_is_named_by_a_row():
    """The other direction. A test no row names was never proposed and is never reviewed."""
    named = {node for row in _test_rows() for node in _listed(row[5])}
    unrecorded = sorted(_defined() - named)
    assert unrecorded == []


def test_every_path_a_dev_row_owns_is_tracked():
    """Three `Paths it owns` entries outlived the commit that deleted their files."""
    tracked = _tracked()
    dirs = {name.rsplit("/", 1)[0] for name in tracked}
    dead = [
        f"{row[0]} owns {path}"
        for row in _dev_rows()
        for path in _listed(row[3])
        if not path.startswith(FOREIGN)
        and path not in tracked
        and path.rstrip("/") not in dirs
        and not any(name.startswith(path.rstrip("/") + "/") for name in tracked)
    ]
    assert dead == []


def test_every_row_names_at_least_one_row_in_the_other_document():
    """A row covering nothing is a claim with no counterpart, in either direction.

    `(deletion)` is the one marked exemption, and `D-50` is the only row holding
    it. A symbol written and never read leaves no behaviour to grade, and a test
    asserting a private name stays absent is a worse liability than the row.
    """
    barren = [
        row[0]
        for row in _dev_rows()
        if not re.search(r"T-\d+", row[4]) and not row[4].startswith(FOREIGN)
    ]
    barren += [row[0] for row in _test_rows() if not re.search(r"D-\d+", row[3])]
    assert barren == []


def _ids(text: str, letter: str) -> set[str]:
    """Every ID a document names, with `T-94..T-101` expanded to its interior.

    Eight dev rows write a range, and a token match recovers only the two ends
    of one. The six IDs between them went unchecked.
    """
    out = set()
    for lo, hi in re.findall(rf"{letter}-(\d+)\.\.{letter}?-?(\d+)", text):
        out.update(f"{letter}-{n}" for n in range(int(lo), int(hi) + 1))
    out.update(re.findall(rf"{letter}-\d+", text))
    return out


def test_no_id_is_an_orphan_in_either_direction():
    """An ID one document names and the other does not hold."""
    dev_ids = {row[0] for row in _dev_rows()}
    test_ids = {row[0] for row in _test_rows()}
    orphans = sorted(_ids(TEST_PLAN.read_text(encoding="utf-8"), "D") - dev_ids)
    orphans += sorted(_ids(DEV_PLAN.read_text(encoding="utf-8"), "T") - test_ids)
    assert orphans == []
