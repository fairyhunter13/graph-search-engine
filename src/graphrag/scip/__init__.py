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

__all__ = ["CoverageError", "IngestReport", "RunError", "auto_indexers", "enabled", "overlay", "plan"]


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


def enabled(project_scip: bool | None) -> bool:
    """Off only where the project says so, or the environment disables it.

    `None` is auto: the overlay is free to run, and `plan` decides per
    language whether an installed indexer backs it. `False` opts out.
    """
    return project_scip is not False and config.SCIP_ENABLED


def auto_indexers(conn: sqlite3.Connection, root: Path | str) -> list[str]:
    """Every indexer this project can run unattended, with no config at all.

    `ready` needs no help. `installable` needs help only where the indexer's
    own dependency marker is missing, so an indexer with no such marker
    (`deps` empty, as `scip-go`'s module cache is) is trusted at
    `installable` too. `scip-typescript` and `scip-php` name a marker, so
    they are auto-selected only where it is already on disk: the overlay
    never runs `npm ci` or `composer install` to manufacture one.
    """
    return sorted(
        row["indexer"]
        for row in run.readiness(root, _languages(conn))
        if row["tier"] == "ready" or (row["tier"] == "installable" and not row["deps"])
    )


def plan(conn: sqlite3.Connection, root: Path | str, cfg) -> list[str]:
    """The indexers one pass should run: named, or worked out, or none.

    Empty where the overlay is off. A project that names `scip_indexers`
    keeps that list exactly, install state included, because naming a tool
    is asking for its refusal to be reported rather than silently skipped.
    Naming none falls back to `auto_indexers`.
    """
    if not enabled(cfg.scip):
        return []
    if cfg.scip_indexers:
        return sorted(cfg.scip_indexers)
    return auto_indexers(conn, root)
