"""The query surface behind the MCP tools. Locations and edges, never bodies.

An edge that crosses a file is not stored. It is derived here, from the `refs`
and `imports` rows one file wrote alone, because index time may not read a
second file. A same-file and a same-class edge is stored, so the two sources are
disjoint and no answer counts a reference twice.

Every answer carries the capability of the languages it touched. A language with
no call capture answers a caller question with a gap, and the gap is written
into the answer rather than left as an empty list. An empty list here reads as
"nothing calls this", which is the confidently wrong answer this engine exists
to avoid.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from . import config, dbread, derive, grammars, store, traverse

# The edge kinds each question walks. A question outside this map is an error
# naming the valid set, never a widened corpus.
QUESTIONS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "callers": (traverse.UPSTREAM, ("CALLS",), "calls"),
    "callees": (traverse.DOWNSTREAM, ("CALLS",), "calls"),
    "implementations": (traverse.UPSTREAM, ("IMPLEMENTS",), "impls"),
    "importers": (traverse.UPSTREAM, ("IMPORTS",), "imports"),
    "imports": (traverse.DOWNSTREAM, ("IMPORTS",), "imports"),
    "references": (traverse.UPSTREAM, ("REFERENCES", "CALLS"), "calls"),
}

_FTS = (
    "SELECT n.id, n.name, n.qualified_name, n.kind, n.start_line, n.end_line, f.path, f.lang "
    "FROM nodes_fts JOIN nodes n ON n.id = nodes_fts.rowid JOIN files f ON f.id = n.file_id "
    "WHERE nodes_fts MATCH ? ORDER BY rank LIMIT ?"
)


# What a partial answer says about itself. A scan that stopped and did not say so
# reads as complete, which is the confidently wrong answer this engine avoids.
_TRUNCATED = (
    f"more than {dbread.REF_SCAN_CAP} references spell a name on this walk, so the scan "
    "stopped and this answer is partial"
)


@dataclass(slots=True)
class Hit:
    node_id: int
    name: str
    qualified_name: str
    kind: str
    path: str
    lang: str
    line: int
    end_line: int


@dataclass(slots=True)
class Answer:
    """Results plus what the engine could not see. `gaps` is the honest half."""

    question: str
    results: list[traverse.Reached] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    ambiguous: int = 0
    capabilities: dict[str, list[str]] = field(default_factory=dict)


def _quote(term: str) -> str:
    """FTS5 takes an identifier as a quoted phrase, so `foo_bar` is one token."""
    return '"' + term.replace('"', '""') + '"'


def find_symbol(conn: sqlite3.Connection, name: str, *, limit: int = 20) -> list[Hit]:
    """Names and qualified names over FTS5. Locations, never bodies."""
    rows = conn.execute(_FTS, (_quote(name), limit)).fetchall()
    return [
        Hit(
            node_id=row["id"],
            name=row["name"],
            qualified_name=row["qualified_name"],
            kind=row["kind"],
            path=row["path"],
            lang=row["lang"],
            line=row["start_line"],
            end_line=row["end_line"],
        )
        for row in rows
    ]


def _languages(conn: sqlite3.Connection) -> list[str]:
    return [
        row["lang"]
        for row in conn.execute("SELECT DISTINCT lang FROM files WHERE lang != '' ORDER BY lang")
    ]


def capability_report(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """What each language in this project can answer. `doctor` prints it whole."""
    return {lang: sorted(grammars.capabilities(lang)) for lang in _languages(conn)}


def _gaps(conn: sqlite3.Connection, wanted: str) -> list[str]:
    """One line per language in the project that cannot answer this question."""
    out = []
    for lang in _languages(conn):
        note = grammars.missing(lang, wanted)
        if note:
            out.append(note)
    return out


# How many same-named definitions a start resolution reads before it picks. A
# name is a handful of definitions in practice, and the pool is only there to be
# counted and named.
_START_POOL = 20


def _start_candidates(conn: sqlite3.Connection, symbol: str) -> list[Hit]:
    """Every definition that spells this name, exact matches first.

    FTS5 tokenizes a compound node name, so a module node called
    `package:a/b/widget` matches the query `Widget` and can outrank the methods
    that carry the name itself. An exact hit on `name` or
    `qualified_name` is a definition the caller asked for. The rest merely share
    a token, and letting one of those win the start meant the answer belonged to
    a node the caller never named.
    """
    hits = find_symbol(conn, symbol, limit=_START_POOL)
    exact = [hit for hit in hits if symbol in (hit.name, hit.qualified_name)]
    return exact or hits


def _homonyms(pool: list[Hit]) -> str:
    """The gap a start with several candidates prints.

    An answer for one of four definitions is not wrong, but silence about the
    other three reads as an answer about the name. `ambiguous` cannot carry
    this: it counts the candidates of each edge, so a start with four homonyms
    and one clean edge each reports zero.
    """
    chosen, others = pool[0], pool[1:]
    shown = ", ".join(
        f"{hit.qualified_name or hit.name} at {hit.path}:{hit.line}" for hit in others[:4]
    )
    more = f", and {len(others) - 4} more" if len(others) > 4 else ""
    return (
        f"{len(pool)} definitions spell this name, so this answer is for "
        f"{chosen.qualified_name or chosen.name} at {chosen.path}:{chosen.line} alone. "
        f"The others are {shown}{more}. Ask again with a qualified name or a node id "
        f"to reach one of them."
    )


def _resolve_start(conn: sqlite3.Connection, symbol: str | int) -> tuple[int | None, list[Hit]]:
    """The start node, and every candidate that spelled the name beside it."""
    if isinstance(symbol, int):
        return symbol, []
    pool = _start_candidates(conn, symbol)
    return (pool[0].node_id if pool else None), pool


_REFS_SPELLING = "SELECT COUNT(*) AS c FROM refs WHERE name = ?"


def _node_name(conn: sqlite3.Connection, node_id: int) -> str:
    row = conn.execute("SELECT name FROM nodes WHERE id = ?", (node_id,)).fetchone()
    return row["name"] if row else ""


def _unreached(conn: sqlite3.Connection, name: str, reached: int) -> str:
    """The gap an upstream answer owes when references spell the name and miss it.

    A caller question walks from the definition back through resolution, so a
    reference the resolver cannot place is a reference this answer never counts.
    A Go method called through a field receiver is the case that matters: the
    receiver's type is not resolved to the package that declares the method, so
    the definition is never a candidate, and `include_ambiguous` does not reach
    it either. A call on the method's own receiver is no longer in that set --
    `refs.receiver_self` resolves it inside the package. The count is the whole
    point. An empty list beside "17 references spell this name" is a gap a
    reader can act on, where an empty list alone reads as nothing calling it.
    """
    if not name:
        return ""
    spelled = conn.execute(_REFS_SPELLING, (name,)).fetchone()["c"]
    if spelled <= reached:
        return ""
    return (
        f"{spelled} references in this project spell {name!r} and {reached} of them resolved "
        f"to this definition, so this answer understates. A method reached through a field "
        f"receiver, an expression receiver, or a local variable whose type comes from an "
        f"assignment is not resolved to its declaration, and a reference the resolver cannot "
        f"place is never counted here."
    )


def neighbors(
    conn: sqlite3.Connection,
    symbol: str | int,
    *,
    question: str = "callers",
    include_ambiguous: bool = False,
) -> Answer:
    """One hop from a symbol, in the direction the question names."""
    if question not in QUESTIONS:
        raise ValueError(f"question must be one of {sorted(QUESTIONS)}, not {question!r}")
    direction, kinds, wanted = QUESTIONS[question]
    answer = Answer(question=question, capabilities=capability_report(conn))
    answer.gaps = _gaps(conn, wanted)

    start, pool = _resolve_start(conn, symbol)
    if start is None:
        answer.gaps.insert(0, f"no symbol named {symbol!r} is indexed in this project")
        return answer
    if len(pool) > 1:
        answer.gaps.insert(0, _homonyms(pool))

    stored = traverse.one_hop(
        conn, start, direction=direction, kinds=kinds, include_ambiguous=include_ambiguous
    )
    ctx = dbread.Context(conn)
    derived, truncated = derive.hop(
        ctx, start, direction=direction, kinds=kinds, include_ambiguous=include_ambiguous
    )
    if truncated:
        answer.gaps.append(_TRUNCATED)
    answer.results = derive.merge(stored, derived)
    if direction == traverse.UPSTREAM:
        start_name = pool[0].name if pool else _node_name(conn, start)
        note = _unreached(conn, start_name, len(answer.results))
        if note:
            answer.gaps.append(note)
    # Ambiguity is the candidate count, never the confidence. A same-file call
    # scores 0.95 with exactly one candidate, so a confidence test reported
    # every one of them as a guess and the number meant nothing.
    answer.ambiguous = sum(1 for r in answer.results if r.candidate_count > 1)
    return answer


def blast_radius(
    conn: sqlite3.Connection,
    symbol: str | int,
    *,
    depth: int = 3,
    include_ambiguous: bool = False,
) -> Answer:
    """Transitive dependents, bounded. Over the ceiling is an error, not a truncation."""
    if depth > config.MAX_DEPTH:
        raise ValueError(f"depth {depth} is over the ceiling of {config.MAX_DEPTH}")
    answer = Answer(question="blast_radius", capabilities=capability_report(conn))
    answer.gaps = _gaps(conn, "calls")

    start, pool = _resolve_start(conn, symbol)
    if start is None:
        answer.gaps.insert(0, f"no symbol named {symbol!r} is indexed in this project")
        return answer
    if len(pool) > 1:
        answer.gaps.insert(0, _homonyms(pool))

    answer.results, truncated = derive.radius(
        conn, start, depth=depth, include_ambiguous=include_ambiguous
    )
    if truncated:
        answer.gaps.append(_TRUNCATED)
    # Ambiguity is the candidate count, never the confidence. A same-file call
    # scores 0.95 with exactly one candidate, so a confidence test reported
    # every one of them as a guess and the number meant nothing.
    answer.ambiguous = sum(1 for r in answer.results if r.candidate_count > 1)
    return answer


def project_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """What the reach notice prints: nodes, edges and the resolved share."""
    return store.counts(conn)
