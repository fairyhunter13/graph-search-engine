"""The batched write of one resolved pass into the store.

Nodes before edges, because an edge names two node ids and both have to exist.
A module node per file carries the imports and owns the top-level definitions,
so a file with no symbols still has somewhere to hang an edge. A name the repo
never defines gets no node at all: it is an unresolved `refs` row, which the
query reports as a fact rather than as a synthetic symbol.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from .discover import FileMeta
from .extract import FileFacts, Reference
from .resolve import Resolution
from .symtab import SymbolTable

# `(path, definition index)`, which is what the symbol table hands back. The
# module node of a file is index `-1`, because a module is not in the list.
Key = tuple[str, int]
MODULE_INDEX = -1

_NODE_INSERT = (
    "INSERT INTO nodes(file_id, kind, name, qualified_name, start_byte, end_byte, "
    "start_line, end_line, body_end_byte) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?) "
    "ON CONFLICT(file_id, start_byte, end_byte) DO UPDATE SET kind = excluded.kind, "
    "name = excluded.name, qualified_name = excluded.qualified_name"
)


def _tier(facts: FileFacts | None) -> tuple[str, str]:
    """The tier, and why it is not higher. A `none` tier always carries a reason,
    and the converse does not hold: `query_failed` rides beside `symbols` where one
    query matched and the other raised."""
    if facts is None:
        return "none", "no_symbols"
    if facts.error:
        return "none", facts.reason
    if facts.definitions or facts.references:
        return "symbols", facts.reason
    if facts.imports:
        return "imports", facts.reason
    return "none", facts.reason or "no_symbols"


def _node_id(conn: sqlite3.Connection, file_id: int, start: int, end: int) -> int:
    row = conn.execute(
        "SELECT id FROM nodes WHERE file_id = ? AND start_byte = ? AND end_byte = ?",
        (file_id, start, end),
    ).fetchone()
    return row["id"]


def write_files(
    conn: sqlite3.Connection, metas: Iterable[FileMeta], facts_by_path: dict[str, FileFacts]
) -> dict[str, int]:
    """Insert or replace one row per file, and return `{rel_path: file_id}`."""
    ids: dict[str, int] = {}
    for meta in metas:
        facts = facts_by_path.get(meta.rel_path)
        tier, reason = _tier(facts)
        conn.execute(
            "INSERT INTO files(path, mtime, size, sha256, lang, n_lines, tier, reason) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(path) DO UPDATE SET mtime = excluded.mtime, size = excluded.size, "
            "sha256 = excluded.sha256, lang = excluded.lang, n_lines = excluded.n_lines, "
            "tier = excluded.tier, reason = excluded.reason",
            (
                meta.rel_path,
                meta.mtime,
                meta.size,
                meta.sha256,
                meta.lang,
                facts.n_lines if facts else 0,
                tier,
                reason,
            ),
        )
        ids[meta.rel_path] = conn.execute(
            "SELECT id FROM files WHERE path = ?", (meta.rel_path,)
        ).fetchone()["id"]
    return ids


def _overlaps(taken: list[tuple[int, int]], start: int, end: int) -> bool:
    """Whether an identifier range already claimed covers part of this one.

    `UNIQUE(file_id, start_byte, end_byte)` catches an exact repeat only, and two
    symbol sources naming one identifier rarely agree to the byte. The module
    node is zero-width at 0, so it claims nothing and collides with nothing.
    """
    if end <= start:
        return False
    return any(start < taken_end and taken_start < end for taken_start, taken_end in taken)


def write_nodes(
    conn: sqlite3.Connection, table: SymbolTable, file_ids: dict[str, int]
) -> dict[Key, int]:
    """One module node per file plus one node per definition, keyed for edges."""
    nodes: dict[Key, int] = {}
    for path, facts in table.files.items():
        file_id = file_ids.get(path)
        if file_id is None:
            continue
        rows: list[tuple] = [
            (MODULE_INDEX, "module", table.path_module.get(path, path), "", 0, 0, 0, 0, 0)
        ]
        taken: list[tuple[int, int]] = []
        for i, d in enumerate(facts.definitions):
            if _overlaps(taken, d.start_byte, d.end_byte):
                continue
            taken.append((d.start_byte, d.end_byte))
            rows.append(
                (
                    i,
                    d.kind,
                    d.name,
                    d.qualified_name,
                    d.start_byte,
                    d.end_byte,
                    d.start_line,
                    d.end_line,
                    d.body_end_byte,
                )
            )
        for index, *values in rows:
            conn.execute(_NODE_INSERT, (file_id, *values))
            nodes[(path, index)] = _node_id(conn, file_id, values[3], values[4])
    return nodes


def write_refs(
    conn: sqlite3.Connection, deferred: dict[str, list[Reference]], file_ids: dict[str, int]
) -> int:
    """One row per reference the file could not decide by itself.

    The receiver and `is_member` are what `resolve._receiver_modules` narrows on,
    and both were consumed into edges and dropped before this. A reference the
    file did decide is an edge instead, so no query counts one twice.
    """
    rows: list[tuple] = []
    for path, refs in deferred.items():
        file_id = file_ids.get(path)
        if file_id is None:
            continue
        for ref in refs:
            rows.append(
                (
                    file_id,
                    ref.kind,
                    ref.name,
                    ref.receiver,
                    1 if ref.is_member else 0,
                    ref.call_site_byte,
                    ref.line,
                )
            )
    conn.executemany(
        "INSERT INTO refs(file_id, kind, name, receiver, is_member, call_site_byte, line) "
        "VALUES(?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def write_imports(
    conn: sqlite3.Connection, facts_by_path: dict[str, FileFacts], file_ids: dict[str, int]
) -> int:
    """One row per import, carrying the raw module string the source wrote.

    Raw, and not resolved. Module identity is per-language and still wrong in
    most of them, so a resolved string here would freeze today's answer into the
    store. The query resolves it on read and improves with no reindex.
    """
    rows: list[tuple] = []
    for path, facts in facts_by_path.items():
        file_id = file_ids.get(path)
        if file_id is None or facts.error:
            continue
        for row in facts.imports:
            rows.append((file_id, row.module, row.symbol, row.alias, row.line))
    conn.executemany(
        "INSERT INTO imports(file_id, module, symbol, alias, line) VALUES(?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def structural_edges(table: SymbolTable, nodes: dict[Key, int]) -> list[tuple]:
    """CONTAINS and DEFINES, which need no resolution: the AST already said so."""
    rows: list[tuple] = []
    for path, facts in table.files.items():
        module = nodes.get((path, MODULE_INDEX))
        if module is None:
            continue
        for i, definition in enumerate(facts.definitions):
            child = nodes.get((path, i))
            if child is None:
                continue
            parent = nodes.get((path, definition.parent)) if definition.parent is not None else None
            src, kind = (parent, "CONTAINS") if parent is not None else (module, "DEFINES")
            rows.append((src, child, kind, 1.0, 1, 1, "same_file", 0, "treesitter"))
    return rows


def reference_edges(
    path: str,
    resolutions: Iterable[Resolution],
    nodes: dict[Key, int],
) -> list[tuple]:
    """One edge per surviving candidate, never one edge per reference."""
    rows: list[tuple] = []
    module = nodes.get((path, MODULE_INDEX))
    for res in resolutions:
        ref = res.reference
        src = nodes.get((path, ref.scope)) if ref.scope is not None else module
        if src is None:
            continue
        count = res.candidate_count
        for hit in res.candidates:
            dst = nodes.get((hit.symbol.path, hit.symbol.index))
            if dst is None:
                continue
            resolved = 1 if count == 1 else 0
            rows.append(
                (
                    src,
                    dst,
                    ref.kind,
                    hit.confidence,
                    count,
                    resolved,
                    hit.evidence,
                    ref.call_site_byte,
                    "treesitter",
                )
            )
    return rows


def write_edges(conn: sqlite3.Connection, rows: Iterable[tuple]) -> int:
    rows = list(rows)
    conn.executemany(
        "INSERT INTO edges(src, dst, kind, confidence, candidate_count, resolved, evidence, "
        "call_site_byte, producer) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def forget_files(conn: sqlite3.Connection, paths: Iterable[str]) -> int:
    """Drop each named file, its FTS postings first. Returns the rows deleted.

    The order is the whole function. `nodes_fts` is external-content and takes no
    cascade, so the postings have to go before the rows they were built from. An
    external-content `'delete'` is given the **old** column values, and giving it
    anything else leaves the old postings in place: `find_symbol` then answers a
    renamed symbol under its former name, at a location that no longer exists.
    """
    gone = 0
    for path in paths:
        row = conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()
        if row is None:
            continue
        old = conn.execute(
            "SELECT id, name, qualified_name, signature FROM nodes WHERE file_id = ?",
            (row["id"],),
        ).fetchall()
        conn.executemany(
            "INSERT INTO nodes_fts(nodes_fts, rowid, name, qualified_name, signature) "
            "VALUES('delete', ?, ?, ?, ?)",
            [tuple(r) for r in old],
        )
        conn.execute("DELETE FROM files WHERE id = ?", (row["id"],))
        gone += 1
    return gone


def write_fts(conn: sqlite3.Connection, file_ids: Iterable[int]) -> None:
    """Index the nodes of each rewritten file. The delete above is the other half."""
    for file_id in file_ids:
        conn.execute(
            "INSERT INTO nodes_fts(rowid, name, qualified_name, signature) "
            "SELECT id, name, qualified_name, signature FROM nodes WHERE file_id = ?",
            (file_id,),
        )


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Rebuild every posting from `nodes`. The SCIP overlay's half of the contract.

    The pass itself no longer calls this, because rebuilding every posting is the
    cost a per-file rewrite exists to remove. The overlay still needs it: it
    updates `qualified_name` and can insert nodes, and neither reaches the index.
    """
    conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')")
