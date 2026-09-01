"""The batched write of one resolved pass into the store.

Nodes before edges, because an edge names two node ids and both have to exist.
A module node per file carries the imports and owns the top-level definitions,
so a file with no symbols still has somewhere to hang an edge. External names
get one synthetic file row: a name the repo never defines is a real node with a
real id, and it is never folded onto an in-repo homonym.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from .discover import FileMeta
from .extract import FileFacts
from .resolve import Resolution
from .symtab import SymbolTable, resolve_module

EXTERNAL_PATH = "<external>"

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


def _tier(facts: FileFacts | None) -> str:
    if facts is None or facts.error:
        return "none"
    if facts.definitions or facts.references:
        return "symbols"
    return "imports" if facts.imports else "none"


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
        conn.execute(
            "INSERT INTO files(path, mtime, size, sha256, lang, n_lines, tier) "
            "VALUES(?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(path) DO UPDATE SET mtime = excluded.mtime, size = excluded.size, "
            "sha256 = excluded.sha256, lang = excluded.lang, n_lines = excluded.n_lines, "
            "tier = excluded.tier",
            (
                meta.rel_path,
                meta.mtime,
                meta.size,
                meta.sha256,
                meta.lang,
                facts.n_lines if facts else 0,
                _tier(facts),
            ),
        )
        ids[meta.rel_path] = conn.execute(
            "SELECT id FROM files WHERE path = ?", (meta.rel_path,)
        ).fetchone()["id"]
    return ids


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
        for i, d in enumerate(facts.definitions):
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


def write_externals(conn: sqlite3.Connection, names: Iterable[str]) -> dict[str, int]:
    """A node per name the repo never defines. The byte range is a serial."""
    names = sorted(set(names))
    if not names:
        return {}
    conn.execute(
        "INSERT INTO files(path, mtime, size, sha256, lang, n_lines, tier) "
        "VALUES(?, 0, 0, '', '', 0, 'none') ON CONFLICT(path) DO NOTHING",
        (EXTERNAL_PATH,),
    )
    file_id = conn.execute("SELECT id FROM files WHERE path = ?", (EXTERNAL_PATH,)).fetchone()["id"]
    ids: dict[str, int] = {}
    for offset, name in enumerate(names):
        conn.execute(_NODE_INSERT, (file_id, "external", name, name, offset, offset, 0, 0, 0))
        ids[name] = _node_id(conn, file_id, offset, offset)
    return ids


def write_refs(
    conn: sqlite3.Connection, facts_by_path: dict[str, FileFacts], file_ids: dict[str, int]
) -> int:
    """One row per reference, exactly as the file wrote it.

    The receiver and `is_member` are what `resolve._receiver_modules` narrows on,
    and both were consumed into edges and dropped before this.
    """
    rows: list[tuple] = []
    for path, facts in facts_by_path.items():
        file_id = file_ids.get(path)
        if file_id is None or facts.error:
            continue
        for ref in facts.references:
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


def import_edges(table: SymbolTable, nodes: dict[Key, int]) -> list[tuple]:
    """A module to module edge per import that names a file this repo holds."""
    by_module = {module: path for path, module in table.path_module.items()}
    rows: list[tuple] = []
    for path, facts in table.files.items():
        src = nodes.get((path, MODULE_INDEX))
        if src is None:
            continue
        for row in facts.imports:
            target = by_module.get(resolve_module(path, row.module))
            dst = nodes.get((target, MODULE_INDEX)) if target else None
            if dst is not None and dst != src:
                rows.append((src, dst, "IMPORTS", 1.0, 1, 1, "import", 0, "treesitter"))
    return rows


def reference_edges(
    path: str,
    resolutions: Iterable[Resolution],
    nodes: dict[Key, int],
    externals: dict[str, int],
) -> list[tuple]:
    """One edge per surviving candidate, never one edge per reference."""
    rows: list[tuple] = []
    module = nodes.get((path, MODULE_INDEX))
    for res in resolutions:
        ref = res.reference
        src = nodes.get((path, ref.scope)) if ref.scope is not None else module
        if src is None:
            continue
        if res.external:
            dst = externals.get(ref.name)
            if dst is not None:
                site = ref.call_site_byte
                rows.append((src, dst, ref.kind, 1.0, 1, 1, "external", site, "treesitter"))
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


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Called after the pass has replaced `files` wholesale.

    There is no incremental delete here and the rebuild is why: `nodes_fts` is
    external-content, so the cascade from `files` never reaches it and a search
    would keep answering with symbols the graph no longer holds.
    """
    conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')")
