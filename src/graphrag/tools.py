"""Four tools, because a graph answers four shapes of question.

Everything else is the CLI, because everything else is an operator job. Each
answer carries the capability of the languages it touched, and every gap the
engine knows about rides in `gaps`. A tool here never returns a bare empty list:
an empty list reads as "nothing calls this", and 23 of the 68 grammars with a
tags file emit no call capture at all.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from . import config, federation, index, query, registry, store

INSTRUCTIONS = """\
Structural code search over the graph: who calls this, what breaks if I change
this, what implements this.

- Run `coderag` first and this second. `coderag` ranks by meaning, so it finds
  the code when you have the wrong word for it. This returns an edge, which no
  ranking over text produces. Use `coderag` to get the name, then `neighbors`
  or `blast_radius` to get the facts about it.
- `find_symbol` takes an exact name and returns locations, never bodies.
- `neighbors` is one hop. `question` is one of callers, callees, imports,
  importers, implementations, references.
- `blast_radius` is the transitive form, bounded by `depth`.
- Every answer carries `gaps` and `capabilities`. Where a language has no
  capability for the question, that is an answer and not an absence. Say the
  gap out loud rather than reporting that nothing calls the symbol.
- Results carry `confidence` and `evidence`, so a fact and a ranked guess are
  distinguishable. Ambiguous edges are excluded unless you ask for them.
"""

mcp = MCPServer(name=config.APP, version="0.1.0", instructions=INSTRUCTIONS)


def _rows(reached) -> list[dict[str, Any]]:
    return [
        {
            "name": r.name,
            "qualified_name": r.qualified_name,
            "kind": r.kind,
            "path": r.path,
            "line": r.line,
            "depth": r.depth,
            "edge_kind": r.edge_kind,
            "confidence": round(r.confidence, 4),
            "evidence": r.evidence,
        }
        for r in reached
    ]


def _answer(answer: query.Answer) -> dict[str, Any]:
    return {
        "question": answer.question,
        "results": _rows(answer.results),
        "gaps": answer.gaps,
        "ambiguous": answer.ambiguous,
        "capabilities": answer.capabilities,
    }


def _connect(root: str) -> tuple[Path, sqlite3.Connection]:
    """Open one project's graph, or say why it cannot be opened.

    A store that does not exist is not an empty graph. It is a project nobody
    has indexed, and the reply names `index` rather than answering nothing.
    """
    target = registry.resolve(root)
    path = config.index_path(target)
    if not path.exists():
        raise LookupError(f"{target} has no graph yet, so call index on it first")
    return target, store.connect(path)


def enroll(root: Path | str) -> dict[str, Any]:
    """Claim a project and queue a pass. Shared with the daemon's `/register`.

    The route's caller is a SessionStart hook standing in the directory, and the
    tool's caller is a model naming one. Both need the same work done.
    """
    target = registry.resolve(root)
    if not target.is_dir():
        return {"error": f"{target} is not a directory"}
    members = federation.register(target)
    state = index.QUEUE.submit(target)
    for member in members:
        index.QUEUE.submit(member)
    out: dict[str, Any] = {
        "root": str(target),
        "members": [str(member) for member in members],
        "queued": state,
        "depth": index.QUEUE.depth,
    }
    path = config.index_path(target)
    if path.exists():
        conn = store.connect(path)
        try:
            out |= query.project_counts(conn)
            out["capabilities"] = query.capability_report(conn)
        finally:
            conn.close()
    return out


@mcp.tool(
    name="index",
    description="Enrol a project and queue a graph pass. Returns immediately; "
    "the pass runs in the background. Call again to read the counts.",
    structured_output=True,
)
def index_project(root: str) -> dict[str, Any]:
    return enroll(root)


@mcp.tool(
    name="find_symbol",
    description="Find a symbol by exact name over the graph. Returns locations "
    "-- path, line range and kind -- never bodies. Use coderag to find the name "
    "when you do not have it yet.",
    structured_output=True,
)
def find_symbol(name: str, root: str, limit: int = 20) -> dict[str, Any]:
    try:
        _, conn = _connect(root)
    except LookupError as exc:
        return {"error": str(exc), "results": []}
    try:
        hits = query.find_symbol(conn, name, limit=limit)
        return {
            "results": [
                {
                    "name": h.name,
                    "qualified_name": h.qualified_name,
                    "kind": h.kind,
                    "path": h.path,
                    "lang": h.lang,
                    "line": h.line,
                    "end_line": h.end_line,
                }
                for h in hits
            ],
            "gaps": [] if hits else [f"no symbol named {name!r} is indexed in this project"],
            "capabilities": query.capability_report(conn),
        }
    finally:
        conn.close()


@mcp.tool(
    name="neighbors",
    description="One hop from a symbol: callers, callees, imports, importers, "
    "implementations or references. An edge is a fact, where a ranked mention is "
    "not. A missing capability is reported, never returned as an empty list.",
    structured_output=True,
)
def neighbors(
    symbol: str, root: str, question: str = "callers", include_ambiguous: bool = False
) -> dict[str, Any]:
    try:
        _, conn = _connect(root)
    except LookupError as exc:
        return {"error": str(exc), "results": []}
    try:
        return _answer(
            query.neighbors(conn, symbol, question=question, include_ambiguous=include_ambiguous)
        )
    except ValueError as exc:
        # Returned rather than raised. An error naming the valid set is
        # something a caller can act on, where a transport failure is not.
        return {"error": str(exc), "results": []}
    finally:
        conn.close()


@mcp.tool(
    name="blast_radius",
    description="Every symbol that transitively depends on this one, bounded by "
    "depth. Terminates over a cycle and counts each dependent once. A depth over "
    "the ceiling is refused rather than truncated.",
    structured_output=True,
)
def blast_radius(
    symbol: str, root: str, depth: int = 3, include_ambiguous: bool = False
) -> dict[str, Any]:
    try:
        _, conn = _connect(root)
    except LookupError as exc:
        return {"error": str(exc), "results": []}
    try:
        return _answer(
            query.blast_radius(conn, symbol, depth=depth, include_ambiguous=include_ambiguous)
        )
    except ValueError as exc:
        return {"error": str(exc), "results": []}
    finally:
        conn.close()
