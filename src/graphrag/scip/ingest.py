"""Bring one SCIP index into the store, and refuse a collapsed one.

The guard in `guard.py` runs first, and a refusal writes nothing.

Nothing here extracts. A node is upserted on `(file_id, start_byte, end_byte)`,
the identifier token range both tiers produce, and a call edge is rewritten only
where tree-sitter already found a call at that byte. SCIP cannot tell a call
from a name mention, so that intersection is what the two tiers produce together
and neither produces alone.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .. import dbread
from . import offsets, read, run, symbol
from .guard import Coverage, CoverageError, _key, check, coverage


def _text(root: Path, rel: str, document: read.Document) -> str:
    if document.text:
        return document.text
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


@dataclass(slots=True)
class IngestReport:
    coverage: Coverage = field(default_factory=Coverage)
    nodes: int = 0
    implements: int = 0
    calls: int = 0
    stale: int = 0


def _stale(root: Path, rel: str, built: float) -> bool:
    """Whether the file moved after the artifact was written.

    An occurrence is a byte range into the text the indexer read. A file edited
    since holds different bytes at the same range, so a span that still lands on
    a node lands on the wrong one — and it lands at confidence 1.0, above every
    ranked candidate it replaces. Skipping the document leaves the syntactic
    edge standing, which is the weaker answer and the true one.
    """
    try:
        return (root / rel).stat().st_mtime > built
    except OSError:
        return True


def _node_at(conn: sqlite3.Connection, file_id: int, start: int, end: int) -> int | None:
    row = conn.execute(
        "SELECT id FROM nodes WHERE file_id = ? AND start_byte = ? AND end_byte = ?",
        (file_id, start, end),
    ).fetchone()
    return row["id"] if row else None


def _upgrade_node(
    conn: sqlite3.Connection, node_id: int, info: read.SymbolInfo | None, sets_kind: bool
) -> None:
    """SCIP wins on the descriptive fields, and on `kind` only where it is set.

    `kind` 0 is not `Unspecified` as an answer. It is five indexers leaving the
    field alone, so overwriting a tree-sitter kind with it loses real data.
    """
    if info is None:
        conn.execute("UPDATE nodes SET tier = 'scip' WHERE id = ?", (node_id,))
        return
    kind = symbol.kind_of(info.kind) if sets_kind else ""
    conn.execute(
        "UPDATE nodes SET doc = ?, qualified_name = ?, kind = COALESCE(NULLIF(?, ''), kind), "
        "tier = 'scip' WHERE id = ?",
        ("\n".join(info.documentation), info.symbol, kind, node_id),
    )


def _ref_caller(ctx: dbread.Context, file_id: int, site: int) -> int | None:
    """The node a deferred reference belongs to, or None where there is no such
    reference. A call that leaves its file is a `refs` row and never an edge."""
    row = ctx.conn.execute(
        "SELECT 1 FROM refs WHERE file_id = ? AND call_site_byte = ? AND kind = 'CALLS'",
        (file_id, site),
    ).fetchone()
    if row is None:
        return None
    return ctx.enclosing(file_id, site) or dbread.module_node(ctx, file_id)


def _rewrite_call(ctx: dbread.Context, file_id: int, site: int, dst: int, tool: str) -> bool:
    """Replace the ranked candidates at one call site with the one SCIP names.

    Only where tree-sitter already recorded a call at this byte. A SCIP
    occurrence alone is a name mention, and treating one as a call is how this
    tier would start inventing edges instead of upgrading them.

    The parse records a call in one of two places. A call its own file decides
    is a stored edge, and a call that leaves the file is a `refs` row. Both are
    the parse's own record, so the tier upgrades either one. The `refs` row
    stays where it is, and `derive` skips a site this tier already decided, so
    an answer carries one edge and never two.
    """
    rows = ctx.conn.execute(
        "SELECT e.id AS id, e.src AS src FROM edges e JOIN nodes n ON n.id = e.src "
        "WHERE n.file_id = ? AND e.call_site_byte = ? AND e.kind = 'CALLS'",
        (file_id, site),
    ).fetchall()
    src = rows[0]["src"] if rows else _ref_caller(ctx, file_id, site)
    if src is None:
        return False
    ctx.conn.executemany("DELETE FROM edges WHERE id = ?", [(r["id"],) for r in rows])
    ctx.conn.execute(
        "INSERT INTO edges(src, dst, kind, confidence, candidate_count, resolved, evidence, "
        "call_site_byte, producer) VALUES(?, ?, 'CALLS', 1.0, 1, 1, 'scip', ?, ?)",
        (src, dst, site, tool),
    )
    return True


def ingest(
    conn: sqlite3.Connection,
    path: Path | str,
    root: Path | str,
    prefix: str = "",
    deeper: tuple[str, ...] = (),
) -> IngestReport:
    """One index, guarded then applied. A refusal raises and writes nothing.

    `root` is the project, never the build unit. An index written inside a
    sub-module names its documents relative to that module, so `prefix`
    re-bases them onto the paths the store holds, and `deeper` keeps the
    grading to the files this unit is the nearest one above.
    """
    root = Path(root)
    built = Path(path).stat().st_mtime
    meta = read.metadata(path)
    got = run.indexer(meta.tool_name)
    report = IngestReport(
        coverage=coverage(conn, path, meta.tool_name, got.languages, prefix, deeper)
    )
    reason = check(report.coverage)
    if reason:
        raise CoverageError(reason)

    files = {row["path"]: row["id"] for row in conn.execute("SELECT id, path FROM files")}
    nodes: dict[str, int] = {}
    references: list[tuple[int, int, str]] = []
    implements: list[tuple[str, str]] = []

    for document in read.documents(path):
        key = _key(prefix, document.relative_path)
        file_id = files.get(key)
        if file_id is None:
            continue
        if _stale(root, key, built):
            report.stale += 1
            continue
        text = _text(root, key, document)
        if not text:
            continue
        table = offsets.Offsets.build(text)
        infos = {info.symbol: info for info in document.symbols}
        units = offsets.encoding_for(meta.tool_name, document.encoding)
        for occurrence in document.occurrences:
            if occurrence.span is None or symbol.is_local(occurrence.symbol):
                continue
            start, end = table.span(occurrence.span, units)
            if occurrence.is_definition:
                node_id = _node_at(conn, file_id, start, end)
                if node_id is None:
                    continue
                _upgrade_node(conn, node_id, infos.get(occurrence.symbol), got.sets_kind)
                nodes[occurrence.symbol] = node_id
                report.nodes += 1
            else:
                references.append((file_id, start, occurrence.symbol))
        if got.emits_relationships:
            implements += [
                (info.symbol, rel.symbol)
                for info in document.symbols
                for rel in info.relationships
                if rel.is_implementation
            ]

    ctx = dbread.Context(conn)
    for file_id, site, name in references:
        dst = nodes.get(name)
        if dst is not None and _rewrite_call(ctx, file_id, site, dst, meta.tool_name):
            report.calls += 1

    # This producer's own implements edges, dropped before they are written again.
    # A call edge is keyed by its byte and replaces itself; an implements edge is
    # keyed by nothing, so a second ingest of one index doubled every one of them.
    conn.execute("DELETE FROM edges WHERE kind = 'IMPLEMENTS' AND producer = ?", (meta.tool_name,))

    for child, parent in implements:
        src, dst = nodes.get(child), nodes.get(parent)
        if src is None or dst is None or src == dst:
            continue
        conn.execute(
            "INSERT INTO edges(src, dst, kind, confidence, candidate_count, resolved, evidence, "
            "call_site_byte, producer) VALUES(?, ?, 'IMPLEMENTS', 1.0, 1, 1, 'scip', 0, ?)",
            (src, dst, meta.tool_name),
        )
        report.implements += 1
    return report
