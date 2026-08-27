"""Bring one SCIP index into the store, and refuse a collapsed one.

The guard runs before any write, and it is not optional. `scip-python` never
sets `autoSearchPaths`, so on a `src/` layout it drops every cross-package
reference and exits 0. Counting its documents and definitions against the
tree-sitter census is the only thing that tells that run from a working one.

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

from .. import config
from . import offsets, read, run, symbol


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


@dataclass(slots=True)
class IngestReport:
    coverage: Coverage = field(default_factory=Coverage)
    nodes: int = 0
    implements: int = 0
    calls: int = 0


def _census(
    conn: sqlite3.Connection, languages: tuple[str, ...]
) -> tuple[int, int, dict[str, int]]:
    """Tree-sitter's own count for the languages this indexer claims."""
    marks = ",".join("?" * len(languages))
    files = {
        row["path"]: row["id"]
        for row in conn.execute(f"SELECT id, path FROM files WHERE lang IN ({marks})", languages)
    }
    if not files:
        return 0, 0, {}
    ids = ",".join("?" * len(files))
    definitions = conn.execute(
        f"SELECT count(*) AS n FROM nodes WHERE file_id IN ({ids}) AND kind != 'module'",
        tuple(files.values()),
    ).fetchone()["n"]
    return len(files), definitions, files


def coverage(conn: sqlite3.Connection, path: Path | str, tool: str, languages) -> Coverage:
    """Count the index against the census. Reading only, so it never half-writes."""
    census_files, census_definitions, known = _census(conn, tuple(languages))
    got = Coverage(tool=tool, census_files=census_files, census_definitions=census_definitions)
    for document in read.documents(path):
        got.documents += 1
        if document.relative_path not in known:
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


def _text(root: Path, rel: str, document: read.Document) -> str:
    if document.text:
        return document.text
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


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


def _rewrite_call(conn: sqlite3.Connection, file_id: int, site: int, dst: int, tool: str) -> bool:
    """Replace the ranked candidates at one call site with the one SCIP names.

    Only where tree-sitter already recorded a call at this byte. A SCIP
    occurrence alone is a name mention, and treating one as a call is how this
    tier would start inventing edges instead of upgrading them.
    """
    rows = conn.execute(
        "SELECT e.id AS id, e.src AS src FROM edges e JOIN nodes n ON n.id = e.src "
        "WHERE n.file_id = ? AND e.call_site_byte = ? AND e.kind = 'CALLS'",
        (file_id, site),
    ).fetchall()
    if not rows:
        return False
    conn.executemany("DELETE FROM edges WHERE id = ?", [(r["id"],) for r in rows])
    conn.execute(
        "INSERT INTO edges(src, dst, kind, confidence, candidate_count, resolved, evidence, "
        "call_site_byte, producer) VALUES(?, ?, 'CALLS', 1.0, 1, 1, 'scip', ?, ?)",
        (rows[0]["src"], dst, site, tool),
    )
    return True


def ingest(conn: sqlite3.Connection, path: Path | str, root: Path | str) -> IngestReport:
    """One index, guarded then applied. A refusal raises and writes nothing."""
    root = Path(root)
    meta = read.metadata(path)
    got = run.indexer(meta.tool_name)
    report = IngestReport(coverage=coverage(conn, path, meta.tool_name, got.languages))
    reason = check(report.coverage)
    if reason:
        raise CoverageError(reason)

    files = {row["path"]: row["id"] for row in conn.execute("SELECT id, path FROM files")}
    nodes: dict[str, int] = {}
    references: list[tuple[int, int, str]] = []
    implements: list[tuple[str, str]] = []

    for document in read.documents(path):
        file_id = files.get(document.relative_path)
        if file_id is None:
            continue
        text = _text(root, document.relative_path, document)
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

    for file_id, site, name in references:
        dst = nodes.get(name)
        if dst is not None and _rewrite_call(conn, file_id, site, dst, meta.tool_name):
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
