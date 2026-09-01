"""An edge no single file could store, derived on read.

Index time may not read a second file, so a reference that leaves its file is
stored as a bare `refs` row and resolved here. A same-file and a same-class
reference is a stored edge instead, so the two sources are disjoint and no
answer counts a reference twice.
"""

from __future__ import annotations

import sqlite3

from . import dbread, resolvedb, symtab, traverse

# What a blast radius walks. `IMPORTS` is asked beside these, and never with
# them, because it is answered from the `imports` table and not from `refs`.
_RADIUS_KINDS = ("CALLS", "REFERENCES", "IMPLEMENTS")

_NODE = (
    "SELECT n.id, n.name, n.qualified_name, n.kind, n.start_line, f.path "
    "FROM nodes n JOIN files f ON f.id = n.file_id WHERE n.id = ?"
)


def reached(
    ctx: dbread.Context,
    node_id: int,
    *,
    depth: int,
    edge_kind: str,
    confidence: float,
    evidence: str,
    candidate_count: int,
) -> traverse.Reached | None:
    row = ctx.conn.execute(_NODE, (node_id,)).fetchone()
    if row is None:
        return None
    return traverse.Reached(
        node_id=row["id"],
        depth=depth,
        edge_kind=edge_kind,
        confidence=confidence,
        name=row["name"],
        qualified_name=row["qualified_name"],
        kind=row["kind"],
        line=row["start_line"],
        path=row["path"],
        evidence=evidence,
        candidate_count=candidate_count,
    )


def upstream_refs(
    ctx: dbread.Context, start: int, kinds: tuple[str, ...], include_ambiguous: bool
) -> tuple[list[traverse.Reached], bool]:
    """The caller question, inverted. Read every reference that spells the name,
    resolve each one, and keep the rows whose winning candidate is this node."""
    row = ctx.conn.execute("SELECT name FROM nodes WHERE id = ?", (start,)).fetchone()
    if row is None:
        return [], False
    refs, truncated = dbread.refs_naming(ctx, row["name"], kinds)
    out: list[traverse.Reached] = []
    for ref in refs:
        if dbread.decided_by_scip(ctx, ref):
            continue
        res = resolvedb.resolve_ref(ctx, ref)
        if not include_ambiguous and not res.resolved:
            continue
        hit = next((c for c in res.candidates if c.symbol.node_id == start), None)
        if hit is None:
            continue
        src = dbread.caller_node(ctx, ref)
        if src is None or src == start:
            continue
        found = reached(
            ctx,
            src,
            depth=1,
            edge_kind=ref.kind,
            confidence=hit.confidence,
            evidence=hit.evidence,
            candidate_count=res.candidate_count,
        )
        if found is not None:
            out.append(found)
    return out, truncated


def downstream_refs(
    ctx: dbread.Context, start: int, kinds: tuple[str, ...], include_ambiguous: bool
) -> list[traverse.Reached]:
    """The cheap direction: the references this definition's own body makes."""
    out: list[traverse.Reached] = []
    for ref in dbread.refs_inside(ctx, start, kinds):
        if dbread.decided_by_scip(ctx, ref):
            continue
        res = resolvedb.resolve_ref(ctx, ref)
        if not include_ambiguous and not res.resolved:
            continue
        for hit in res.candidates:
            if hit.symbol.node_id == start:
                continue
            found = reached(
                ctx,
                hit.symbol.node_id,
                depth=1,
                edge_kind=ref.kind,
                confidence=hit.confidence,
                evidence=hit.evidence,
                candidate_count=res.candidate_count,
            )
            if found is not None:
                out.append(found)
    return out


def import_hop(ctx: dbread.Context, start: int, upstream: bool) -> list[traverse.Reached]:
    """The two import questions, over the raw module strings.

    A module string is resolved on read, so the answer improves the day module
    identity is fixed and no store is rewritten.
    """
    row = ctx.conn.execute("SELECT file_id FROM nodes WHERE id = ?", (start,)).fetchone()
    if row is None:
        return []
    file_id = row["file_id"]
    files = importing_files(ctx, file_id) if upstream else imported_files(ctx, file_id)
    out: list[traverse.Reached] = []
    for other in files:
        node = dbread.module_node(ctx, other)
        if node is None or node == start:
            continue
        found = reached(
            ctx,
            node,
            depth=1,
            edge_kind="IMPORTS",
            confidence=1.0,
            evidence="import",
            candidate_count=1,
        )
        if found is not None:
            out.append(found)
    return out


def hop(
    ctx: dbread.Context,
    start: int,
    *,
    direction: str,
    kinds: tuple[str, ...],
    include_ambiguous: bool = False,
) -> tuple[list[traverse.Reached], bool]:
    """One hop over the edges no file could store.

    The second value says the reference scan hit its cap, and `neighbors` writes
    that into `gaps`. A truncated answer that does not say so reads as complete.
    """
    if kinds == ("IMPORTS",):
        return import_hop(ctx, start, upstream=direction == traverse.UPSTREAM), False
    if direction == traverse.UPSTREAM:
        return upstream_refs(ctx, start, kinds, include_ambiguous)
    return downstream_refs(ctx, start, kinds, include_ambiguous), False


def merge(
    stored: list[traverse.Reached], derived: list[traverse.Reached]
) -> list[traverse.Reached]:
    """One row per node, at its best confidence. A stored edge and a derived one
    never name the same pair, but two derived rows can: one call site each."""
    best: dict[int, traverse.Reached] = {}
    for row in [*stored, *derived]:
        held = best.get(row.node_id)
        if held is None or (row.depth, -row.confidence) < (held.depth, -held.confidence):
            best[row.node_id] = row
    return sorted(best.values(), key=lambda r: (r.depth, r.path, r.line))


def imported_files(ctx: dbread.Context, file_id: int) -> list[int]:
    """The files one file imports, resolved on read from the raw module string."""
    path = ctx.path_of(file_id)
    index = dbread.by_module(ctx)
    out: list[int] = []
    for row in ctx.conn.execute("SELECT module FROM imports WHERE file_id = ?", (file_id,)):
        for target in index.get(symtab.resolve_module(path, row["module"]), ()):
            if target != file_id and target not in out:
                out.append(target)
    return out


def importing_files(ctx: dbread.Context, file_id: int) -> list[int]:
    """The files that import one file."""
    module = symtab.module_name(ctx.path_of(file_id))
    return sorted(f for f in dbread.importers_by_module(ctx).get(module, set()) if f != file_id)


def radius(
    conn: sqlite3.Connection,
    start: int,
    *,
    depth: int,
    include_ambiguous: bool = False,
) -> tuple[list[traverse.Reached], bool]:
    """The transitive walk, level by level, because half its edges are derived.

    `traverse.walk` is one recursive statement over stored edges, and it cannot
    see a cross-file reference any more. So the levels are driven here, and each
    one asks the two sources `neighbors` asks. A node is counted once, at the
    shortest depth that reaches it.
    """
    ctx = dbread.Context(conn)
    seen = {start}
    out: list[traverse.Reached] = []
    frontier = [start]
    truncated = False
    for level in range(1, depth + 1):
        rows: list[traverse.Reached] = []
        for node in frontier:
            rows += traverse.one_hop(
                conn,
                node,
                direction=traverse.UPSTREAM,
                kinds=(*_RADIUS_KINDS, "IMPORTS"),
                include_ambiguous=include_ambiguous,
            )
            for kinds in (_RADIUS_KINDS, ("IMPORTS",)):
                found, cut = hop(
                    ctx,
                    node,
                    direction=traverse.UPSTREAM,
                    kinds=kinds,
                    include_ambiguous=include_ambiguous,
                )
                rows += found
                truncated = truncated or cut
        frontier = []
        for row in rows:
            if row.node_id in seen:
                continue
            seen.add(row.node_id)
            row.depth = level
            out.append(row)
            frontier.append(row.node_id)
        if not frontier:
            break
    return sorted(out, key=lambda r: (r.depth, r.path, r.line)), truncated
