"""The check that pages when the daemon is up and the fleet is not.

`systemctl is-active` answers whether the process runs, and that stays green
through every project failing to index. So this asks the daemon, and it asks
about the fleet.

Persistence is the whole design. `last_error` is cleared by the next success, so
a transient failure holds one project failing until the next pass. A checker
that paged on one sample would page for nearly all of them, and an alert that
cries wolf is how the outage that mattered goes unread. A project pages only if
it was failing at the previous check too.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from . import config


def _previous(state_path: Path) -> dict:
    try:
        was = json.loads(state_path.read_text(encoding="utf-8"))
        return {"failing": set(was["failing"]), "queue_depth": was.get("queue_depth")}
    except (OSError, ValueError, KeyError, TypeError):
        # A first run, or state we cannot read. Empty means nothing pages this
        # time, which is right: an unreadable history is not evidence of a
        # failure, and the next check has a real previous set to compare.
        return {"failing": set(), "queue_depth": None}


def _silent(body: dict, was: dict) -> tuple[list[str], set[str]]:
    """The failures no project row carries, as identities the same rule can hold.

    A dead worker thread and a queue that stopped draining are both "up and not
    indexing", and neither shows up in `failing`. Each identity is a constant
    string, because the rule compares identities: one carrying a count differs
    between the two samples and therefore pages on neither.

    The second return names the identities that already carry two samples of
    their own. Only the queue does, so running the rule on it twice would page
    three checks after the stall rather than at it.
    """
    silent = []
    if body.get("worker_alive") is False:
        silent.append("indexer:the worker thread is not running")

    proven = set()
    depth = int(body.get("queue_depth") or 0)
    before = was["queue_depth"]
    if depth >= config.HEALTH_QUEUE_STUCK and before is not None and depth >= before:
        stalled = "indexer:the queue is not draining"
        silent.append(stalled)
        proven.add(stalled)

    listed = len(body.get("failing") or [])
    if int(body.get("projects_failing") or 0) > listed:
        silent.append(f"registry:more than {listed} projects failing, past the reply's cap")
    return silent, proven


def check(url: str = "", state_path: Path | None = None, timeout: float = 10.0) -> tuple[bool, str]:
    """`(ok, reason)`. Not ok means it failed at this check and the one before."""
    url = url or config.HEALTHZ_URL
    state_path = state_path or config.HEALTH_STATE_PATH
    try:
        with urllib.request.urlopen(url, timeout=timeout) as reply:
            body = json.loads(reply.read())
    except (OSError, urllib.error.URLError, ValueError) as exc:
        # A daemon that does not answer is one sample of nothing, and it is
        # reported rather than ranked: the graph is unavailable, which is not
        # the same as a project failing to index.
        return False, f"{url} did not answer: {exc}"

    was = _previous(state_path)
    silent, proven = _silent(body, was)
    failing = sorted([str(p) for p in body.get("failing") or []] + silent)
    stuck = sorted((was["failing"] | proven) & set(failing))

    state_path.parent.mkdir(parents=True, exist_ok=True)
    depth = int(body.get("queue_depth") or 0)
    state_path.write_text(
        json.dumps({"failing": failing, "queue_depth": depth}, indent=1), encoding="utf-8"
    )

    total = body.get("projects", "?")
    if stuck:
        return False, f"{len(stuck)} of {total} failing since the last check: " + ", ".join(stuck)
    if failing:
        return True, f"{len(failing)} failing for the first time, watching: " + ", ".join(failing)
    return True, f"{total} projects, none failing"
