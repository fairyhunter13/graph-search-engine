"""One watcher over every enabled project, debounced in Rust before Python.

Two things this shares rather than reimplements. The filter is
`filters.indexable`, the same predicate the indexer uses: a watcher that decides
differently wakes the indexer for files it will then refuse. And the queue is
`index.QUEUE`, so a change lands as a job the one worker serialises.

The re-arm is conditional, and that is the load-bearing part. Re-arming tears
down every inotify watch and rebuilds it. inotify has no replay, so every change
inside that window is lost for good, and a caller that re-armed on every index
call would hold the watcher blind more or less continuously.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from watchfiles import watch as _watch

from . import config, filters, index, ledger, registry

log = logging.getLogger(__name__)

_thread: threading.Thread | None = None
_stop = threading.Event()
_rearm = threading.Event()
# What this pass is arming. `_armed` would be empty until the watches are in
# place, so a comparison against it re-arms once more than it needs to.
_intent: tuple[Path, ...] = ()


def _roots() -> tuple[Path, ...]:
    rows = registry.load()
    return tuple(
        sorted(Path(key) for key, row in rows.items() if row.enabled and Path(key).is_dir())
    )


def rearm_if_changed() -> None:
    """The only entry point. Re-arm when the watched set actually differs."""
    if _roots() != _intent:
        _rearm.set()


def _owner(path: Path, roots: tuple[Path, ...]) -> Path | None:
    """Which watched project a changed path belongs to: the longest match.

    Longest rather than first. A federation member can live inside its root's
    tree, and the first match would file its files under the wrong graph.
    """
    owning = [root for root in roots if path == root or root in path.parents]
    return max(owning, key=lambda root: len(str(root))) if owning else None


def _keep(_change, raw: str) -> bool:
    """The watcher's filter is the indexer's predicate, with no stat.

    A deleted file cannot be stat-ed, and the pass that follows is what notices
    the deletion. Passing a size here would drop exactly that event.
    """
    path = Path(raw)
    return filters.language_of(path) != "" and not any(
        filters.skipped_dir(part) for part in path.parts[:-1]
    )


def _submit(batch: set[tuple[int, str]], roots: tuple[Path, ...]) -> dict[str, int]:
    """One job per project the batch touched, never one job per file."""
    touched: dict[str, int] = {}
    for _kind, raw in batch:
        owner = _owner(Path(raw), roots)
        if owner is None:
            continue
        touched[str(owner)] = touched.get(str(owner), 0) + 1
    for root in touched:
        index.QUEUE.submit(root)
    return touched


def _loop() -> None:
    global _intent
    while not _stop.is_set():
        _intent = _roots()
        if not _intent:
            if _stop.wait(1.0):
                return
            continue

        _rearm.clear()
        log.info("watching %d projects", len(_intent))
        for batch in _watch(
            *_intent,
            watch_filter=_keep,
            stop_event=_stop,
            debounce=config.WATCH_DEBOUNCE_MS,
            rust_timeout=config.WATCH_POLL_MS,
            yield_on_timeout=True,
        ):
            if _rearm.is_set() or _stop.is_set():
                break
            if not batch:
                continue
            touched = _submit(batch, _intent)
            if touched:
                ledger.append(ledger.WATCH, {"events": len(batch), "projects": touched})


def start() -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="watcher", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=10)


def alive() -> bool:
    return _thread is not None and _thread.is_alive()
