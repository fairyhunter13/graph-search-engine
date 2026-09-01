"""The queue that serializes one index pass against the next.

The queue is the write serializer. There is no second write lock, because a
lock plus a queue is two answers to one question and they drift apart.

Its dedup is asymmetric on purpose. A job already queued is dropped, because
the queued pass has not read the tree yet and will see the change. A job whose
root is already *running* is queued again, because the running pass may have
read the tree before the change landed. Losing that re-queue is a missed edit
that never heals until the next full pass.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from pathlib import Path

from . import index, ledger, registry, trace

log = logging.getLogger(__name__)


class Queue:
    """One queue, one worker. The queue is the state, and it is asymmetric."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._waiting: deque[str] = deque()
        self._queued: set[str] = set()
        self._running: set[str] = set()
        self._ready: dict[str, float] = {}
        self._wake = threading.Condition(self._lock)

    def submit(self, root: Path | str, *, delay: float = 0.0) -> str:
        """Returns `queued`, `dropped` or `requeued`, and the third is the point.

        `delay` holds the job until the project has been quiet that long, and a
        further submission restarts the countdown. Saves land a median 11 s
        apart while someone edits, and each one otherwise buys a whole pass.
        """
        key = str(Path(root).resolve())
        with self._wake:
            ready = time.monotonic() + delay
            if key in self._queued:
                # An explicit call pulls a waiting job forward; a further watch
                # event pushes it back.
                self._ready[key] = ready if not delay else max(self._ready[key], ready)
                self._wake.notify()
                return "dropped"
            verdict = "requeued" if key in self._running else "queued"
            self._queued.add(key)
            self._waiting.append(key)
            self._ready[key] = ready
            self._wake.notify()
            return verdict

    def _pop_ready(self) -> str | None:
        now = time.monotonic()
        for key in self._waiting:
            if self._ready[key] <= now:
                self._waiting.remove(key)
                self._queued.discard(key)
                self._ready.pop(key, None)
                self._running.add(key)
                return key
        return None

    def take(self, timeout: float = 1.0) -> str | None:
        with self._wake:
            key = self._pop_ready()
            if key is not None:
                return key
            if self._ready:
                timeout = min(timeout, max(0.0, min(self._ready.values()) - time.monotonic()))
            self._wake.wait(timeout)
            return self._pop_ready()

    def drain(self) -> int:
        """Discard everything waiting, quiet window included.

        `take` skips a job whose countdown is still running, so a caller that
        polls `take` until it returns None cannot empty the queue.
        """
        with self._wake:
            dropped = len(self._waiting)
            self._waiting.clear()
            self._queued.clear()
            self._ready.clear()
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
        key = queue.take()
        if key is None:
            continue
        with trace.span():
            try:
                report = index.index_once(key)
                index.record(report)
                ledger.append(
                    ledger.RUN,
                    {
                        "kind": "index",
                        "root": key,
                        "files": report.files,
                        "parsed": report.parsed,
                        "edges": report.edges,
                        "resolved": report.resolved,
                        "unchanged": report.unchanged,
                        "rebuilt": report.rebuilt,
                    },
                )
            except Exception as exc:
                # The row carries the failure, so the health rule can hold it
                # across two samples. A worker that dies on one project stops
                # indexing every other one.
                registry.mark_indexed(key, error=str(exc))
                ledger.append(ledger.RUN, {"kind": "index", "root": key, "error": str(exc)})
                log.exception("index pass failed for %s", key)
            finally:
                queue.done(key)
