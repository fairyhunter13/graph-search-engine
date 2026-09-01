"""The queue that serializes one index pass against the next.

The queue is the write serializer. There is no second write lock, because a
lock plus a queue is two answers to one question and they drift apart.

Its dedup is asymmetric on purpose. A job already queued is merged into, because
the queued pass has not read the tree yet and will see the change. A job whose
root is already *running* is queued again, because the running pass may have
read the tree before the change landed. Losing that re-queue is a missed edit
that never heals until the next full pass.

A job carries the watcher's hint, and the merge is what keeps it. Dropping the
second submission was safe while a job meant *reindex everything*. It loses the
paths the moment a job names them, and the file then stays stale until the next
unhinted pass.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from . import config, index, ledger, registry, trace

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Job:
    """One pass to run. `paths` is the hint, and `None` means the whole tree."""

    root: str
    paths: frozenset[str] | None = None


def _capped(paths) -> frozenset[str] | None:
    """A hint the pass is cheaper for, or `None` for the whole-tree scan.

    A branch switch moves thousands of files inside one debounce window, and
    rewriting them one at a time costs more than one scan of the tree.
    """
    if paths is None:
        return None
    paths = frozenset(paths)
    if len(paths) > config.WATCH_HINT_MAX_PATHS:
        return None
    return paths


def _merge(left, right) -> frozenset[str] | None:
    """An unhinted job absorbs a hinted one, because a scan covers any hint."""
    if left is None or right is None:
        return None
    return _capped(left | right)


class Queue:
    """One queue, one worker. The queue is the state, and it is asymmetric."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._waiting: deque[str] = deque()
        self._hints: dict[str, frozenset[str] | None] = {}
        self._running: set[str] = set()
        self._wake = threading.Condition(self._lock)

    def submit(self, root: Path | str, *, paths=None) -> str:
        """Returns `queued`, `merged` or `requeued`, and the third is the point."""
        key = str(Path(root).resolve())
        hint = _capped(paths)
        with self._wake:
            if key in self._hints:
                self._hints[key] = _merge(self._hints[key], hint)
                self._wake.notify()
                return "merged"
            verdict = "requeued" if key in self._running else "queued"
            self._hints[key] = hint
            self._waiting.append(key)
            self._wake.notify()
            return verdict

    def _pop(self) -> Job | None:
        if not self._waiting:
            return None
        key = self._waiting.popleft()
        paths = self._hints.pop(key, None)
        self._running.add(key)
        return Job(key, paths)

    def take(self, timeout: float = 1.0) -> Job | None:
        with self._wake:
            job = self._pop()
            if job is not None:
                return job
            self._wake.wait(timeout)
            return self._pop()

    def drain(self) -> int:
        """Discard everything waiting. What is running is not touched."""
        with self._wake:
            dropped = len(self._waiting)
            self._waiting.clear()
            self._hints.clear()
            return dropped

    def done(self, key: str) -> None:
        with self._wake:
            self._running.discard(key)

    @property
    def depth(self) -> int:
        with self._lock:
            return len(self._waiting)


QUEUE = Queue()


def run_worker(queue: Queue = QUEUE, *, stop: threading.Event | None = None) -> None:
    """Drain the queue until told to stop. One thread, so one writer."""
    stop = stop or threading.Event()
    while not stop.is_set():
        job = queue.take()
        if job is None:
            continue
        with trace.span():
            try:
                report = index.index_once(job.root, paths=job.paths)
                index.record(report)
                ledger.append(
                    ledger.RUN,
                    {
                        "kind": "index",
                        "root": job.root,
                        "files": report.files,
                        "parsed": report.parsed,
                        "edges": report.edges,
                        "resolved": report.resolved,
                        "unchanged": report.unchanged,
                        "hinted": report.hinted,
                        "rebuilt": report.rebuilt,
                    },
                )
            except Exception as exc:
                # The row carries the failure, so the health rule can hold it
                # across two samples. A worker that dies on one project stops
                # indexing every other one.
                registry.mark_indexed(job.root, error=str(exc))
                ledger.append(ledger.RUN, {"kind": "index", "root": job.root, "error": str(exc)})
                log.exception("index pass failed for %s", job.root)
            finally:
                queue.done(job.root)
