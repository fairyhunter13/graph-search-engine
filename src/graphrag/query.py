"""The query surface behind the MCP tools. Locations and edges, never bodies.

Every answer carries the capability of the languages it touched. A language with
no call capture answers a caller question with a gap, and the gap is written
into the answer rather than left as an empty list. An empty list here reads as
"nothing calls this", which is the confidently wrong answer this engine exists
to avoid.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from . import config, grammars, store, traverse

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
    "WHERE nodes_fts MATCH ? AND n.kind != 'external' ORDER BY rank LIMIT ?"
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


def _resolve_start(conn: sqlite3.Connection, symbol: str | int) -> int | None:
    if isinstance(symbol, int):
        return symbol
    hits = find_symbol(conn, symbol, limit=1)
    return hits[0].node_id if hits else None


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

    start = _resolve_start(conn, symbol)
    if start is None:
        answer.gaps.insert(0, f"no symbol named {symbol!r} is indexed in this project")
        return answer

    answer.results = traverse.one_hop(
        conn, start, direction=direction, kinds=kinds, include_ambiguous=include_ambiguous
    )
    answer.ambiguous = sum(1 for r in answer.results if r.confidence < 1.0)
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

    start = _resolve_start(conn, symbol)
    if start is None:
        answer.gaps.insert(0, f"no symbol named {symbol!r} is indexed in this project")
        return answer

    answer.results = traverse.walk(
        conn,
        start,
        direction=traverse.UPSTREAM,
        depth=depth,
        kinds=("CALLS", "REFERENCES", "IMPORTS", "IMPLEMENTS"),
        include_ambiguous=include_ambiguous,
    )
    answer.ambiguous = sum(1 for r in answer.results if r.confidence < 1.0)
    return answer


def project_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """What the reach notice prints: nodes, edges and the resolved share."""
    return store.counts(conn)
