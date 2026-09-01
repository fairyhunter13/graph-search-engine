"""Whether one SCIP index covers enough of the tree to be believed.

The guard runs before any write, and it is not optional. `scip-python` never
sets `autoSearchPaths`, so on a `src/` layout it drops every cross-package
reference and exits 0. Counting its documents and definitions against the
tree-sitter census is the only thing that tells that run from a working one.

Reading only. Nothing here touches a row, which is what lets a refusal cost the
project nothing it already had.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .. import config
from . import read


class CoverageError(RuntimeError):
    """A SCIP index that covers too little of the tree to be believed."""


@dataclass(slots=True)
class Coverage:
    """What the index holds, against what tree-sitter already found."""

    tool: str = ""
    documents: int = 0
    matched: int = 0
    definitions: int = 0
    census_files: int = 0
    census_definitions: int = 0

    @property
    def file_share(self) -> float:
        return self.matched / self.census_files if self.census_files else 0.0

    @property
    def definition_share(self) -> float:
        return self.definitions / self.census_definitions if self.census_definitions else 0.0


def _key(prefix: str, rel: str) -> str:
    """A document path, re-based from its build unit onto the project root."""
    return f"{prefix}/{rel}" if prefix else rel


def _owns(path: str, prefix: str, deeper: tuple[str, ...]) -> bool:
    """Whether this build unit is the nearest one above a file.

    A unit prefix contains every deeper unit's files as well, so the root
    module of a multi-module repository would otherwise be graded against the
    whole tree and refused for covering 0% of it.
    """
    if prefix and not path.startswith(f"{prefix}/"):
        return False
    return not any(path.startswith(f"{d}/") for d in deeper)


def _census(
    conn: sqlite3.Connection,
    languages: tuple[str, ...],
    prefix: str = "",
    deeper: tuple[str, ...] = (),
) -> tuple[int, int, dict[str, int]]:
    """Tree-sitter's own count for the languages this indexer claims."""
    marks = ",".join("?" * len(languages))
    files = {
        row["path"]: row["id"]
        for row in conn.execute(f"SELECT id, path FROM files WHERE lang IN ({marks})", languages)
        if _owns(row["path"], prefix, deeper)
    }
    if not files:
        return 0, 0, {}
    ids = ",".join("?" * len(files))
    definitions = conn.execute(
        f"SELECT count(*) AS n FROM nodes WHERE file_id IN ({ids}) AND kind != 'module'",
        tuple(files.values()),
    ).fetchone()["n"]
    return len(files), definitions, files


def coverage(
    conn: sqlite3.Connection,
    path: Path | str,
    tool: str,
    languages,
    prefix: str = "",
    deeper: tuple[str, ...] = (),
) -> Coverage:
    """Count the index against the census. Reading only, so it never half-writes."""
    census_files, census_definitions, known = _census(conn, tuple(languages), prefix, deeper)
    got = Coverage(tool=tool, census_files=census_files, census_definitions=census_definitions)
    for document in read.documents(path):
        got.documents += 1
        if _key(prefix, document.relative_path) not in known:
            continue
        got.matched += 1
        got.definitions += sum(1 for o in document.occurrences if o.is_definition and o.span)
    return got


def check(got: Coverage) -> str:
    """Why this index is refused, or an empty string.

    A reason and not a boolean, because the operator who sees a refusal needs to
    know whether the build was wrong or the thresholds are.
    """
    if got.census_files == 0:
        return f"no file in this project is a language {got.tool} indexes"
    if got.file_share < config.SCIP_FILE_COVERAGE:
        return (
            f"{got.tool} covers {got.matched} of {got.census_files} files "
            f"({got.file_share:.0%}), under the {config.SCIP_FILE_COVERAGE:.0%} floor"
        )
    if got.definition_share < config.SCIP_DEF_COVERAGE:
        return (
            f"{got.tool} defines {got.definitions} symbols against tree-sitter's "
            f"{got.census_definitions} ({got.definition_share:.0%}), under the "
            f"{config.SCIP_DEF_COVERAGE:.0%} floor"
        )
    return ""
