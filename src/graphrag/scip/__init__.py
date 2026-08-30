"""The SCIP overlay. Optional, isolable, and deletable in one move.

It never extracts. Tree-sitter owns the census of files, definitions and call
sites, and this tier upgrades what that census already found. SCIP silence is
not the absence of a call, so a symbol this tier says nothing about keeps its
import-scoped ranked candidates.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .. import config
from . import ingest, read, run
from .ingest import CoverageError, IngestReport
from .run import OUTPUT_NAME, RunError

__all__ = ["CoverageError", "IngestReport", "RunError", "overlay"]


def _languages(conn: sqlite3.Connection) -> frozenset[str]:
    """The languages tree-sitter actually found here, from its own file census."""
    rows = conn.execute("SELECT DISTINCT lang FROM files WHERE lang != ''")
    return frozenset(row[0] for row in rows)


def overlay(conn: sqlite3.Connection, root: Path | str, indexers: list[str]) -> dict[str, str]:
    """Apply every named indexer over a project, and report each one's outcome.

    A refusal is an outcome and never an exception here. One collapsed index
    must not cost the project the graph tree-sitter already built, and an
    operator needs to read which tool was refused and by how much.

    An indexer whose languages the project does not hold is skipped before it is
    invoked. A root names its indexers once and its members inherit the list, so
    without this a Go indexer starts a Go build in every PHP repository the root
    federates. The skip is reported, never silent.

    A project is indexed one build unit at a time. An indexer resolves the
    build it stands in, so a repository holding several `go.mod` files needs one
    invocation each, and a unit that refuses costs the others nothing.

    An index this tier writes lands beside the graph, never in the project. The
    engine indexes trees it does not own, and `config.index_path` already keeps
    the graph out for the same reason. An `index.scip` an operator put in the
    project is still read, because that is how an indexer needing its own build
    hands its work over.
    """
    root = Path(root).resolve()
    present = _languages(conn)
    beside = config.index_path(root).parent
    out: dict[str, str] = {}
    for name in indexers:
        got = run.indexer(name)
        if not present.intersection(got.languages):
            out[name] = f"skipped: project holds none of {', '.join(got.languages)}"
            continue
        prefixes = run.units(name, root)
        done: list[str] = []
        for prefix in prefixes:
            deeper = tuple(
                other
                for other in prefixes
                if other and other != prefix and other.startswith(f"{prefix}/" if prefix else "")
            )
            try:
                said = _unit(conn, root, beside, got, prefix, deeper)
            except (RunError, CoverageError, ValueError) as exc:
                said = f"refused: {exc}"
            done.append(said if len(prefixes) == 1 else f"{prefix or '.'}: {said}")
        out[name] = "; ".join(done)
    return out


def _unit(
    conn: sqlite3.Connection,
    root: Path,
    beside: Path,
    got: run.Indexer,
    prefix: str,
    deeper: tuple[str, ...],
) -> str:
    """Run and ingest one build unit, and report what it moved."""
    here = root / prefix if prefix else root
    path = here / OUTPUT_NAME
    if not path.exists() and got.command:
        tag = f"-{prefix.replace('/', '-')}" if prefix else ""
        path = run.run(got.name, here, out=beside / f"{got.name}{tag}.scip")
    if not path.exists():
        raise RunError(f"no SCIP index at {path}")
    if read.metadata(path).tool_name != got.name:
        raise RunError(f"{path} was not written by {got.name}")
    report = ingest.ingest(conn, path, root, prefix, deeper)
    return f"{report.nodes} nodes, {report.calls} calls, {report.implements} implementations"


def enabled(project_scip: bool) -> bool:
    """Off unless the project asks and the environment has not disabled it."""
    return project_scip and config.SCIP_ENABLED
