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


def overlay(conn: sqlite3.Connection, root: Path | str, indexers: list[str]) -> dict[str, str]:
    """Apply every named indexer over a project, and report each one's outcome.

    A refusal is an outcome and never an exception here. One collapsed index
    must not cost the project the graph tree-sitter already built, and an
    operator needs to read which tool was refused and by how much.
    """
    root = Path(root).resolve()
    out: dict[str, str] = {}
    for name in indexers:
        try:
            got = run.indexer(name)
            path = root / OUTPUT_NAME
            if not path.exists() and got.command:
                path = run.run(name, root)
            if not path.exists():
                raise RunError(f"no SCIP index at {path}")
            if read.metadata(path).tool_name != name:
                raise RunError(f"{path} was not written by {name}")
            report = ingest.ingest(conn, path, root)
            out[name] = (
                f"{report.nodes} nodes, {report.calls} calls, {report.implements} implementations"
            )
        except (RunError, CoverageError, ValueError) as exc:
            out[name] = f"refused: {exc}"
    return out


def enabled(project_scip: bool) -> bool:
    """Off unless the project asks and the environment has not disabled it."""
    return project_scip and config.SCIP_ENABLED
