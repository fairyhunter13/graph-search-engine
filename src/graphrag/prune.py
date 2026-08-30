"""Removing a project the filesystem says is gone, on the event and never a scan.

`registry.py` refused this until 2026-08-30, and the refusal was bought with an
incident: a prune by predicate emptied a fleet when a volume went away. Its
argument was that an unmounted volume, a repo moved for ten seconds and a member
behind a broken link all look the same. That is true of a scan. It is not true of
a delete event, and this module is the difference.

Three tests separate a deletion from the other two, and a row dies only when all
three agree.

1. The trigger is one `deleted` event on the path itself. A sweep of the disk
   never starts a removal here.
2. The parent directory must still exist. A repo removed leaves its parent
   standing. An unmounted volume takes the parent with it.
3. A grace period must pass, and the path must still be gone at the end of it.
   A `git clone` into a moved-aside path settles well inside it.

The link case is separate and weaker. A member link removed while its target
lives releases one root's claim, and `registry.release` already deletes the row
only when nothing else claims it.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from . import federation, registry

log = logging.getLogger(__name__)

# Long enough for a checkout, a restore or a move to settle. Short enough that
# the two engines do not disagree about the fleet for a whole minute.
GRACE_SECONDS = 30.0


def looks_deleted(path: Path | str) -> bool:
    """The path is gone and its parent is not. The unmount test, in one line."""
    target = Path(path)
    if target.exists() or target.is_symlink():
        return False
    parent = target.parent
    return parent != target and parent.is_dir()


@dataclass(slots=True)
class _Pending:
    due: float


class Pruner:
    """Deletions waiting out their grace period. One instance per process.

    The clock is injected so a test spends no wall time. Nothing here starts a
    thread: `run_due` is called by the watcher loop, which is already awake.
    """

    def __init__(self, *, grace: float = GRACE_SECONDS, clock=time.monotonic) -> None:
        self._grace = grace
        self._clock = clock
        self._lock = threading.Lock()
        self._gone: dict[str, _Pending] = {}
        self._unlinked: dict[str, _Pending] = {}

    def note_gone(self, key: Path | str) -> None:
        """A registered project's own directory was deleted."""
        with self._lock:
            self._gone[str(Path(key))] = _Pending(due=self._clock() + self._grace)

    def note_unlinked(self, root: Path | str) -> None:
        """A member link under `root` was deleted. The target may well survive."""
        with self._lock:
            self._unlinked[str(Path(root))] = _Pending(due=self._clock() + self._grace)

    @property
    def depth(self) -> int:
        with self._lock:
            return len(self._gone) + len(self._unlinked)

    def _take_due(self) -> tuple[list[str], list[str]]:
        now = self._clock()
        with self._lock:
            gone = [k for k, p in self._gone.items() if p.due <= now]
            unlinked = [k for k, p in self._unlinked.items() if p.due <= now]
            for key in gone:
                del self._gone[key]
            for key in unlinked:
                del self._unlinked[key]
        return sorted(gone), sorted(unlinked)

    def run_due(self) -> dict[str, list[str]]:
        """Act on every deletion whose grace period has run out.

        Returns what it did, so the caller writes one ledger line rather than
        reading the registry back to find out.
        """
        gone, unlinked = self._take_due()
        if not gone and not unlinked:
            # The loop calls this on every tick, including the empty one that
            # `yield_on_timeout` produces. Nothing due must cost nothing.
            return {"forgotten": [], "unclaimed": []}
        rows = registry.load()
        # Re-confirmed here, at the end of the grace period. A path that came
        # back inside the window reaches this line and fails the test.
        dead = [key for key in gone if key in rows and looks_deleted(key)]
        forgotten: list[str] = []
        if dead:
            dropped, released = registry.forget(dead)
            forgotten = sorted({*dropped, *released})
            log.info("forgot %d deleted project(s): %s", len(forgotten), ", ".join(forgotten))

        # `unclaimed` is the claim dropped, and `forgotten` is the row gone.
        # They differ whenever a second root still claims the member, which is
        # the whole reason this path calls `release` and never `forget`.
        unclaimed: list[str] = []
        for root in unlinked:
            if not Path(root).is_dir():
                continue
            for member in federation.sweep(root)[1]:
                unclaimed.append(str(member))
                if registry.get(member) is None:
                    forgotten.append(str(member))
        if unclaimed:
            log.info("released %d member(s) whose link is gone", len(unclaimed))
        return {"forgotten": sorted(set(forgotten)), "unclaimed": sorted(set(unclaimed))}


PRUNER = Pruner()
