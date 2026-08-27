"""The notice a session opens with, and the enrolment that is the larger half.

A SessionStart hook stands in a directory and speaks plain HTTP. It has no MCP
client roots, so it cannot call a tool, which is why the daemon carries
`/register` and why this module posts to it rather than importing the tools.

Four variants, and every one of them is honest. The unreachable variant is the
one that matters: it says the graph is unavailable and structural questions are
unanswered. It never says nothing calls the symbol, because an absent daemon and
an absent edge look identical to a reader and mean opposite things.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from . import config, registry


def register(root: Path | str, url: str = "", timeout: float = 10.0) -> dict:
    """Enrol a root with the running daemon, or say why it could not be."""
    body = json.dumps({"root": str(registry.resolve(root))}).encode()
    request = urllib.request.Request(
        url or config.REGISTER_URL, data=body, headers={"content-type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:
            return json.loads(reply.read())
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return {"unreachable": f"{exc}"}


def _capability_line(capabilities: dict) -> str:
    """Which languages here answer a caller question, and which do not."""
    answers = sorted(lang for lang, caps in capabilities.items() if "calls" in caps)
    silent = sorted(lang for lang, caps in capabilities.items() if "calls" not in caps)
    parts = []
    if answers:
        parts.append(f"caller questions are answered for {', '.join(answers)}")
    if silent:
        parts.append(f"{', '.join(silent)} emit no call capture, so a gap there is not an absence")
    return ". ".join(parts)


def notice(root: Path | str, url: str = "") -> str:
    """The text a session opens with. One of four, and never an empty string."""
    target = registry.resolve(root)
    answer = register(target, url)
    if "unreachable" in answer:
        return (
            f"graphrag: the daemon on {config.PORT} did not answer, so the graph is "
            f"unavailable this session. Structural questions are unanswered rather than "
            f"empty: do not read a missing answer as nothing calling the symbol."
        )
    if "error" in answer:
        return f"graphrag: {answer['error']}"
    if "nodes" not in answer:
        return (
            f"graphrag: {target} is enrolled and a pass is queued, so the graph is not "
            f"answerable yet. Ask again once the pass lands."
        )
    said = (
        f"graphrag: {target} holds {answer['nodes']} nodes and {answer['edges']} edges, "
        f"{answer['resolved']} of them resolved."
    )
    caps = _capability_line(answer.get("capabilities") or {})
    return f"{said} {caps}" if caps else said
