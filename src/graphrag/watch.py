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

from . import config, federation, filters, index, ledger, prune, registry

log = logging.getLogger(__name__)

_thread: threading.Thread | None = None
_stop = threading.Event()
_rearm = threading.Event()
# What this pass is arming. `_armed` would be empty until the watches are in
# place, so a comparison against it re-arms once more than it needs to.
_intent: tuple[Path, ...] = ()
# The registry's mtime and size at the last parse. A row added by another
# process is invisible here until this pair moves.
_stamp: tuple[int, int] | None = None
# Read by `_keep`, which runs per event and must not touch the registry or the
# disk. Both are rebuilt once per arm, beside `_intent`.
_keys: frozenset[str] = frozenset()
_links: dict[str, str] = {}


def _roots() -> tuple[Path, ...]:
    rows = registry.load()
    return tuple(
        sorted(Path(key) for key, row in rows.items() if row.enabled and Path(key).is_dir())
    )


def rearm_if_changed() -> None:
    """The only entry point. Re-arm when the watched set actually differs.

    The registry file is stat'ed before it is parsed, because this runs on every
    one-second tick. `graphrag index` enrols from a separate process, so the
    file's own mtime is the only signal this one gets that a row appeared.
    """
    global _stamp
    try:
        status = config.REGISTRY_PATH.stat()
    except OSError:
        return
    stamp = (status.st_mtime_ns, status.st_size)
    if stamp == _stamp:
        return
    _stamp = stamp
    if _roots() != _intent:
        _rearm.set()


def _owner(path: Path, roots: tuple[Path, ...]) -> Path | None:
    """Which watched project a changed path belongs to: the longest match.

    Longest rather than first. A federation member can live inside its root's
    tree, and the first match would file its files under the wrong graph.
    """
    owning = [root for root in roots if path == root or root in path.parents]
    return max(owning, key=lambda root: len(str(root))) if owning else None


def _register_paths(roots: tuple[Path, ...]) -> None:
    """Rebuild the two sets `_keep` reads. Called once per arm, never per event.

    Only a directly enrolled project is walked for links. A member is a leaf
    that some root reached, and walking all of them would cost 360 tree walks
    before the first watch is armed. inotify has no replay, so time spent here
    is time the fleet is blind.
    """
    global _keys, _links
    rows = registry.load()
    _keys = frozenset(rows)
    watched = {str(root) for root in roots}
    found: dict[str, str] = {}
    for key, row in rows.items():
        if not row.direct or key not in watched:
            continue
        for link in federation.links(key):
            found[str(link)] = key
    _links = found


def _keep(_change, raw: str) -> bool:
    """The watcher's filter is the indexer's predicate, with no stat.

    A deleted file cannot be stat-ed, and the pass that follows is what notices
    the deletion. Passing a size here would drop exactly that event.

    A project directory and a member link both carry no extension, so the
    predicate alone drops the two events that mean a project is gone. They are
    admitted by name, out of the sets the last arm built.
    """
    if raw in _keys or raw in _links:
        return True
    path = Path(raw)
    return filters.language_of(path) != "" and not any(
        filters.skipped_dir(part) for part in path.parts[:-1]
    )


def _note_deletions(batch: set[tuple[int, str]]) -> int:
    """Queue a project removal for every deletion of a project or a member link.

    Queued, never done here. The grace period and the re-confirmation are what
    tell a deletion from a checkout, and `prune` owns both.
    """
    noted = 0
    for _kind, raw in batch:
        if raw in _keys and prune.looks_deleted(raw):
            prune.PRUNER.note_gone(raw)
            noted += 1
        owner = _links.get(raw)
        if owner is not None and not Path(raw).is_symlink():
            prune.PRUNER.note_unlinked(owner)
            noted += 1
    return noted


def _submit(batch: set[tuple[int, str]], roots: tuple[Path, ...]) -> dict[str, int]:
    """One job per project the batch touched, never one job per file."""
    touched: dict[str, int] = {}
    for _kind, raw in batch:
        if raw in _keys or raw in _links:
            continue
        owner = _owner(Path(raw), roots)
        if owner is None:
            continue
        touched[str(owner)] = touched.get(str(owner), 0) + 1
    for root in touched:
        index.QUEUE.submit(root, delay=config.WATCH_QUIET_MS / 1000)
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
        _register_paths(_intent)
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
            # Runs on the empty batch too. `yield_on_timeout` is what makes this
            # loop the clock a waiting deletion is measured against.
            pruned = prune.PRUNER.run_due()
            if pruned["forgotten"] or pruned["unclaimed"]:
                ledger.append(ledger.WATCH, {"pruned": pruned})
            # Every tick, and not only after a prune. A row this process never
            # wrote reaches the watch set no other way, and an unwatched row is
            # a project whose changes and whose deletion are both unseen.
            rearm_if_changed()
            if not batch:
                continue
            _note_deletions(batch)
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
