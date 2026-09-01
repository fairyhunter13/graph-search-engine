"""Four tools, because a graph answers four shapes of question.

Everything else is the CLI, because everything else is an operator job. Each
answer carries the capability of the languages it touched, and every gap the
engine knows about rides in `gaps`. A tool here never returns a bare empty list:
an empty list reads as "nothing calls this", and 18 of the 68 grammars with a
tags file emit no call capture at all.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from . import config, federation, jobs, query, registry, store, watch

INSTRUCTIONS = """\
Structural code search over the graph: who calls this, what breaks if I change
this, what implements this.

- Run `coderag` first and this second. `coderag` ranks by meaning, so it finds
  the code when you have the wrong word for it. This returns an edge, which no
  ranking over text produces. Use `coderag` to get the name, then `neighbors`
  or `blast_radius` to get the facts about it.
- `find_symbol` takes an exact name and returns locations, never bodies. It is
  the one tool that spans the federation, and each hit names the project that
  holds it. Pass that project as `root` to every call after it.
- `neighbors` is one hop, over one project. `question` is one of callers, callees, imports,
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
            # The plan says every tool reports this where it opens the ambiguous
            # rows. Without it a caller reads one edge and cannot tell whether
            # nine others were dropped beside it.
            "candidate_count": r.candidate_count,
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
    state = jobs.QUEUE.submit(target)
    for member in members:
        jobs.QUEUE.submit(member)
    # The watcher armed over the rows that existed when it started, and inotify
    # has no replay. Without this the new rows are watched only after a restart:
    # no change is indexed, and no deletion is ever seen.
    watch.rearm_if_changed()
    out: dict[str, Any] = {
        "root": str(target),
        "members": [str(member) for member in members],
        "queued": state,
        "depth": jobs.QUEUE.depth,
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
    description="Find a symbol by exact name across the root and every project "
    "it federates. Returns locations -- project, path, line range and kind -- "
    "never bodies. Each hit names its project, and that project is the `root` "
    "for the `neighbors` or `blast_radius` call after it. No edge crosses a "
    "project boundary: node ids are per-store, and these services talk over "
    "gRPC and events rather than calls.",
    structured_output=True,
)
def find_symbol(name: str, root: str, limit: int = 20, federated: bool = True) -> dict[str, Any]:
    """Search the root, then every project it federates. One store at a time.

    Federated here and nowhere else. A caller asking `neighbors` already knows
    the repo, because this is what told them. A caller asking for a name knows
    only the workspace, and this workspace federates about 360 repos.
    """
    try:
        target = registry.resolve(root)
    except (OSError, ValueError) as exc:
        return {"error": str(exc), "results": []}
    try:
        # The root is opened first and on its own. A root with no graph is a
        # project nobody has indexed, and that names `index`. A member with no
        # graph is a gap, which is a different fact and a different reply.
        _connect(str(target))[1].close()
    except LookupError as exc:
        return {"error": str(exc), "results": []}
    projects = federation.expand(target) if federated else [target]

    results: list[dict[str, Any]] = []
    capabilities: dict[str, Any] = {}
    unindexed: list[str] = []
    for project in projects:
        if len(results) >= limit:
            break
        try:
            _, conn = _connect(str(project))
        except LookupError:
            unindexed.append(str(project))
            continue
        try:
            for hit in query.find_symbol(conn, name, limit=limit - len(results)):
                results.append(
                    {
                        # The owning project, because a path alone does not say
                        # which of 360 graphs the next `neighbors` call names.
                        "project": str(project),
                        "name": hit.name,
                        "qualified_name": hit.qualified_name,
                        "kind": hit.kind,
                        "path": hit.path,
                        "lang": hit.lang,
                        "line": hit.line,
                        "end_line": hit.end_line,
                    }
                )
            if project == target:
                capabilities = query.capability_report(conn)
        finally:
            conn.close()

    gaps: list[str] = []
    if not results:
        scope = "this project" if len(projects) == 1 else f"{len(projects)} federated projects"
        gaps.append(f"no symbol named {name!r} is indexed in {scope}")
    if unindexed:
        # Named, never counted as an absence. An unindexed member is a project
        # nobody has passed, and it answers nothing rather than answering no.
        gaps.append(f"{len(unindexed)} member(s) have no graph yet: {', '.join(unindexed[:5])}")
    return {
        "searched": len(projects),
        "results": results,
        "gaps": gaps,
        "capabilities": capabilities,
    }


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
