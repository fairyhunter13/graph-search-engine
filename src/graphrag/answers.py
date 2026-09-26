"""The row and envelope shape every query tool answers with.

Split out of `tools.py`, which registers and routes the four MCP tools -- a
different concern from shaping what a query answer looks like once it comes
back from `query.py`.
"""

from __future__ import annotations

from typing import Any

from . import query


def rows(reached) -> list[dict[str, Any]]:
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


def to_answer(answer: query.Answer) -> dict[str, Any]:
    return {
        "question": answer.question,
        "results": rows(answer.results),
        "gaps": answer.gaps,
        "ambiguous": answer.ambiguous,
        "capabilities": answer.capabilities,
    }
