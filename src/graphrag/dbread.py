"""Every read a query makes over the store, memoized for the length of one query.

The rule this engine is built on bounds index time, not query time: no index-time
work may read a second file. A query may read what it likes, so the cross-file
half of the graph is read here and scored in `resolvedb`.

Five inputs decide a reference. Four are file-local or pure, and one is global:

    the candidate pool     nodes, on the `nodes_name` index   <- the global read
    the file's imports     imports, on `imports_file`
    the file's module      symtab.module_name(path), pure
    the enclosing class    the stored CONTAINS chain
    the pool's size        the same seek

So a query is two indexed seeks plus one small per-file read, and `Context` is
what makes one file's read serve every reference in it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from . import symtab

# from a truncated scan has to name the truncation rather than look complete.
REF_SCAN_CAP = 200_000

# A definition, never a module node and never a synthetic external. `symtab.build`
# indexes `facts.definitions` only, so the pool here has to match it.
_POOL = (
    "SELECT n.id, n.file_id, n.name, n.kind, n.qualified_name, n.start_byte, f.path "
    "FROM nodes n JOIN files f ON f.id = n.file_id "
    "WHERE n.name = ? AND n.kind != 'module'"
)

_ENCLOSING = (
    "SELECT id FROM nodes WHERE file_id = ? AND start_byte <= ? AND ? < body_end_byte "
    "ORDER BY (body_end_byte - start_byte) ASC, id ASC LIMIT 1"
)


@dataclass(slots=True, frozen=True)
class DbSymbol:
    """A candidate, keyed by node id. `start_byte` is the `_rank` tiebreak.

    `resolve` ties on `Symbol.index`, the ordinal in `FileFacts.definitions`.
    Measured over 938 files in five languages, no file's definitions are out of
    `start_byte` order, so the two orders agree and this one has a column.
    """

    node_id: int
    file_id: int
    path: str
    name: str
    kind: str
    qualified_name: str
    start_byte: int


@dataclass(slots=True, frozen=True)
class DbRef:
    ref_id: int
    file_id: int
    path: str
    kind: str
    name: str
    receiver: str
    is_member: bool
    call_site_byte: int
    line: int


class Context:
    """One connection plus the memos that keep a hot name affordable.

    Every memo is keyed by something the store decides, so a `Context` is only
    valid for one graph and only until that graph is written again. Callers build
    one per query and drop it.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._pool: dict[str, list[DbSymbol]] = {}
        self._imports: dict[int, tuple[dict[str, str], set[str]]] = {}
        self._parent: dict[int, int | None] = {}
        self._kind: dict[int, str] = {}
        self._path: dict[int, str] = {}
        self._by_module: dict[str, list[int]] | None = None
        self._importers: dict[str, set[int]] | None = None
        self._module_node: dict[int, int | None] = {}
        self._scip_sites: dict[int, set[int]] | None = None

    def path_of(self, file_id: int) -> str:
        if file_id not in self._path:
            row = self.conn.execute("SELECT path FROM files WHERE id = ?", (file_id,)).fetchone()
            self._path[file_id] = row["path"] if row else ""
        return self._path[file_id]

    def pool(self, name: str) -> list[DbSymbol]:
        """Every definition of a name in this project. The one global read."""
        if name not in self._pool:
            self._pool[name] = [
                DbSymbol(
                    node_id=row["id"],
                    file_id=row["file_id"],
                    path=row["path"],
                    name=row["name"],
                    kind=row["kind"],
                    qualified_name=row["qualified_name"],
                    start_byte=row["start_byte"],
                )
                for row in self.conn.execute(_POOL, (name,))
            ]
        return self._pool[name]

    def imports(self, file_id: int) -> tuple[dict[str, str], set[str]]:
        """`imported_names` and `imported_modules` for one file, read once.

        A relative module is made absolute here, the way `symtab` does it, so an
        import written `from . import x` names the same thing at query time as
        it did at index time.
        """
        if file_id in self._imports:
            return self._imports[file_id]
        path = self.path_of(file_id)
        names: dict[str, str] = {}
        modules: set[str] = set()
        for row in self.conn.execute(
            "SELECT module, symbol, alias FROM imports WHERE file_id = ?", (file_id,)
        ):
            module = symtab.resolve_module(path, row["module"])
            modules.add(module)
            if row["symbol"]:
                names[row["alias"] or row["symbol"]] = module
            elif row["alias"]:
                names[row["alias"]] = module
        self._imports[file_id] = (names, modules)
        return self._imports[file_id]

    def parent(self, node_id: int) -> int | None:
        """The node that CONTAINS this one. A top-level definition has none."""
        if node_id not in self._parent:
            row = self.conn.execute(
                "SELECT src FROM edges WHERE dst = ? AND kind = 'CONTAINS' LIMIT 1", (node_id,)
            ).fetchone()
            self._parent[node_id] = row["src"] if row else None
        return self._parent[node_id]

    def kind(self, node_id: int) -> str:
        if node_id not in self._kind:
            row = self.conn.execute("SELECT kind FROM nodes WHERE id = ?", (node_id,)).fetchone()
            self._kind[node_id] = row["kind"] if row else ""
        return self._kind[node_id]

    def enclosing(self, file_id: int, byte: int) -> int | None:
        """The innermost definition whose body holds this byte.

        The substitute for the `scope` index `extract` computed and `refs` does
        not store. The module node carries all three byte columns at 0, so it
        never matches and a top-level call site returns None, exactly as `scope`
        did.
        """
        row = self.conn.execute(_ENCLOSING, (file_id, byte, byte)).fetchone()
        return row["id"] if row else None

    def enclosing_class(self, node_id: int | None) -> int | None:
        """The class a call site sits in, walking the containment chain up."""
        seen: set[int] = set()
        cursor = node_id
        while cursor is not None and cursor not in seen:
            seen.add(cursor)
            if self.kind(cursor) == "class":
                return cursor
            cursor = self.parent(cursor)
        return None


def decided_by_scip(ctx: Context, ref: DbRef) -> bool:
    """Whether the SCIP overlay already answered this reference.

    A cross-file call is a `refs` row, and the overlay upgrades one in place
    rather than deleting it. So the derived hop skips the site, or the same call
    arrives twice: once as the compiler's edge and once as a ranked guess.
    """
    if ctx._scip_sites is None:
        out: dict[int, set[int]] = {}
        for row in ctx.conn.execute(
            "SELECT n.file_id AS f, e.call_site_byte AS b FROM edges e "
            "JOIN nodes n ON n.id = e.src WHERE e.evidence = 'scip' AND e.kind = 'CALLS'"
        ):
            out.setdefault(row["f"], set()).add(row["b"])
        ctx._scip_sites = out
    return ref.call_site_byte in ctx._scip_sites.get(ref.file_id, ())


def row_to_ref(ctx: Context, row: sqlite3.Row) -> DbRef:
    return DbRef(
        ref_id=row["id"],
        file_id=row["file_id"],
        path=ctx.path_of(row["file_id"]),
        kind=row["kind"],
        name=row["name"],
        receiver=row["receiver"],
        is_member=bool(row["is_member"]),
        call_site_byte=row["call_site_byte"],
        line=row["line"],
    )


def _kind_clause(kinds: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    if not kinds:
        return "", ()
    return " AND kind IN (" + ",".join("?" * len(kinds)) + ")", kinds


def refs_naming(
    ctx: Context, name: str, kinds: tuple[str, ...] = (), *, cap: int = REF_SCAN_CAP
) -> tuple[list[DbRef], bool]:
    """Every stored reference to a name, and whether the cap cut the scan.

    Ordered by `file_id` so `Context.imports` reads each file once. Reading it
    per row is what turns the measured 10 ms worst case into seconds."""
    clause, params = _kind_clause(kinds)
    sql = f"SELECT * FROM refs WHERE name = ?{clause} ORDER BY file_id, call_site_byte LIMIT ?"
    rows = ctx.conn.execute(sql, (name, *params, cap + 1)).fetchall()
    return [row_to_ref(ctx, row) for row in rows[:cap]], len(rows) > cap


def refs_inside(ctx: Context, node_id: int, kinds: tuple[str, ...] = ()) -> list[DbRef]:
    """The references a definition's own body makes.

    Byte containment selects the candidates and `enclosing` decides them, because
    a call inside a nested function belongs to that function and not to this one.
    """
    node = ctx.conn.execute(
        "SELECT file_id, start_byte, body_end_byte FROM nodes WHERE id = ?", (node_id,)
    ).fetchone()
    if node is None or node["body_end_byte"] <= node["start_byte"]:
        return []
    clause, params = _kind_clause(kinds)
    sql = (
        f"SELECT * FROM refs WHERE file_id = ? AND call_site_byte >= ? AND call_site_byte < ?"
        f"{clause} ORDER BY call_site_byte"
    )
    rows = ctx.conn.execute(
        sql, (node["file_id"], node["start_byte"], node["body_end_byte"], *params)
    ).fetchall()
    out = []
    for row in rows:
        ref = row_to_ref(ctx, row)
        if ctx.enclosing(ref.file_id, ref.call_site_byte) == node_id:
            out.append(ref)
    return out


def caller_node(ctx: Context, ref: DbRef) -> int | None:
    """The node a reference is attributed to: its enclosing definition, or the
    file's module node where it sits at the top level."""
    return ctx.enclosing(ref.file_id, ref.call_site_byte) or module_node(ctx, ref.file_id)


def by_module(ctx: Context) -> dict[str, list[int]]:
    """Every file this project holds, keyed by the module name of its path.

    A whole-tree read, and allowed: the rule bounds index time, not query time.
    It is one row per file."""
    if ctx._by_module is None:
        out: dict[str, list[int]] = {}
        for row in ctx.conn.execute("SELECT id, path FROM files"):
            out.setdefault(symtab.module_name(row["path"]), []).append(row["id"])
        ctx._by_module = out
    return ctx._by_module


def importers_by_module(ctx: Context) -> dict[str, set[int]]:
    """The files that import each module, every relative spelling made absolute."""
    if ctx._importers is None:
        out: dict[str, set[int]] = {}
        sql = "SELECT i.file_id, i.module, f.path FROM imports i JOIN files f ON f.id = i.file_id"
        for row in ctx.conn.execute(sql):
            target = symtab.resolve_module(row["path"], row["module"])
            out.setdefault(target, set()).add(row["file_id"])
        ctx._importers = out
    return ctx._importers


def module_node(ctx: Context, file_id: int) -> int | None:
    """The node that stands for a whole file. Every IMPORTS answer is one of these."""
    if file_id not in ctx._module_node:
        row = ctx.conn.execute(
            "SELECT id FROM nodes WHERE file_id = ? AND kind = 'module' LIMIT 1", (file_id,)
        ).fetchone()
        ctx._module_node[file_id] = row["id"] if row else None
    return ctx._module_node[file_id]
