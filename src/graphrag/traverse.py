"""Recursive traversal with cycle detection, in SQLite rather than in Python.

A blast radius over an import cycle terminates because the walk carries the path
it took and refuses a node already on it. Counting is by node, so a node reached
by three routes appears once at its shortest depth: a dependent that shows up
three times reads as three things to fix.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from . import config

# `dst` to `src` is what breaks: the callers of a thing, not the things it calls.
UPSTREAM = "upstream"
DOWNSTREAM = "downstream"

# The path is a comma-wrapped id list, and the membership test is a substring
# match on `,id,`. Without the commas `,12,` matches inside `,120,`.
_WALK = """
WITH RECURSIVE walk(id, depth, path, kind, confidence, evidence) AS (
  SELECT :start, 0, ',' || :start || ',', '', 1.0, ''
  UNION ALL
  SELECT e.{next}, w.depth + 1, w.path || e.{next} || ',', e.kind, e.confidence, e.evidence
  FROM edges e JOIN walk w ON e.{here} = w.id
  WHERE w.depth < :depth
    AND instr(w.path, ',' || e.{next} || ',') = 0
    AND e.confidence >= :floor
    AND (:resolved = 0 OR e.resolved = 1)
    AND (:kinds IS NULL OR instr(:kinds, ',' || e.kind || ',') > 0)
)
SELECT w.id, MIN(w.depth) AS depth, w.kind, w.confidence, w.evidence,
       n.name, n.qualified_name, n.kind AS node_kind, n.start_line, f.path AS file
FROM walk w JOIN nodes n ON n.id = w.id JOIN files f ON f.id = n.file_id
WHERE w.depth > 0
GROUP BY w.id
ORDER BY depth, f.path, n.start_line
"""


@dataclass(slots=True)
class Reached:
    """One node the walk reached, at the shortest depth that reaches it."""

    node_id: int
    depth: int
    edge_kind: str
    confidence: float
    name: str
    qualified_name: str
    kind: str
    line: int
    path: str
    # What the edge was resolved by: same_file, import, package, global, scip.
    # A caller reading confidence alone cannot tell a same-file call from a
    # repo-global guess that happens to have one candidate.
    evidence: str = ""


def _columns(direction: str) -> tuple[str, str]:
    if direction == UPSTREAM:
        return "dst", "src"
    if direction == DOWNSTREAM:
        return "src", "dst"
    raise ValueError(f"direction must be {UPSTREAM!r} or {DOWNSTREAM!r}, not {direction!r}")


def walk(
    conn: sqlite3.Connection,
    start: int,
    *,
    direction: str = UPSTREAM,
    depth: int = 0,
    kinds: tuple[str, ...] = (),
    include_ambiguous: bool = False,
    floor: float = 0.0,
) -> list[Reached]:
    """Every node reachable from `start`, bounded and de-duplicated."""
    here, next_ = _columns(direction)
    sql = _WALK.format(here=here, next=next_)
    rows = conn.execute(
        sql,
        {
            "start": start,
            "depth": depth or config.MAX_DEPTH,
            "floor": floor,
            "resolved": 0 if include_ambiguous else 1,
            "kinds": "," + ",".join(kinds) + "," if kinds else None,
        },
    ).fetchall()
    return [
        Reached(
            node_id=row["id"],
            depth=row["depth"],
            edge_kind=row["kind"],
            confidence=row["confidence"],
            name=row["name"],
            qualified_name=row["qualified_name"],
            kind=row["node_kind"],
            line=row["start_line"],
            path=row["file"],
            evidence=row["evidence"],
        )
        for row in rows
    ]


def one_hop(
    conn: sqlite3.Connection,
    start: int,
    *,
    direction: str = UPSTREAM,
    kinds: tuple[str, ...] = (),
    include_ambiguous: bool = False,
) -> list[Reached]:
    """The neighbours of a node. A walk of depth one, so one code path answers both."""
    return walk(
        conn,
        start,
        direction=direction,
        depth=1,
        kinds=kinds,
        include_ambiguous=include_ambiguous,
    )
