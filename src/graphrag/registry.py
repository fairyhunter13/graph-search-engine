"""projects.json: one row per resolved path, mutated under an flock.

Two rules here are copied from the semantic engine, and both were bought with
incidents there rather than reasoned out.

The load happens *inside* the lock. Reading first and locking second is a lost
update: two writers each read the rows, each add one, and the second write drops
the first. It was measured once as a registry that kept 34 of 180 rows.

No scan prunes a row because its path is missing from disk. An unmounted volume,
a repo moved for ten seconds, and a member behind a broken symlink all look
identical to a deleted project when you only see the state. So `forget` takes a
list of keys rather than a predicate.

A delete event is the case that is not a scan, and `prune.py` acts on one behind
a parent-exists test and a grace period. It calls `forget` and `release` here,
and it adds no predicate of its own.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import shutil
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from . import config, quarantine
from .entry import ProjectEntry

Rows = dict[str, ProjectEntry]


def resolve(path: Path | str) -> Path:
    """The registry's key. A symlink is a discovery mechanism, never a key.

    Resolving before ownership is decided is the whole point. A relative or
    symlinked path that skips this claims a different row, and every later
    answer files under the wrong root.
    """
    return Path(path).expanduser().resolve()


def _read_unlocked() -> Rows:
    try:
        raw = json.loads(config.REGISTRY_PATH.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"registry at {config.REGISTRY_PATH} is unreadable: {exc}") from exc
    return {p: ProjectEntry.from_json(p, row) for p, row in raw.items()}


def _rotate_backup() -> None:
    if not config.REGISTRY_PATH.exists():
        return
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    shutil.copy2(config.REGISTRY_PATH, config.BACKUP_DIR / f"projects.{stamp}.json")
    for stale in sorted(config.BACKUP_DIR.glob("projects.*.json"), reverse=True)[
        config.BACKUP_KEEP :
    ]:
        stale.unlink(missing_ok=True)


def _write_unlocked(rows: Rows) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    _rotate_backup()
    payload = {p: rows[p].to_json() for p in sorted(rows)}
    tmp = config.REGISTRY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True))
    tmp.replace(config.REGISTRY_PATH)


@contextmanager
def _mutate() -> Generator[Rows]:
    """Exclusive registry access. Mutate the yielded dict; it is written on exit."""
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    with config.REGISTRY_LOCK.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            rows = _read_unlocked()
            yield rows
            _write_unlocked(rows)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


@contextmanager
def _held(mode: int) -> Generator[Rows]:
    """The rows, with the lock still held while the caller reads them."""
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    with config.REGISTRY_LOCK.open("w") as lock:
        fcntl.flock(lock, mode)
        try:
            yield _read_unlocked()
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def load() -> Rows:
    """A snapshot, shared-locked so it never observes a half-written file."""
    with _held(fcntl.LOCK_SH) as rows:
        return rows


def get(path: Path | str) -> ProjectEntry | None:
    return load().get(str(resolve(path)))


def _device(path: Path | str) -> int:
    """Which filesystem answers this path, or 0 where nothing does."""
    try:
        return Path(path).stat().st_dev
    except OSError:
        return 0


def claim(path: Path | str, *, direct: bool = False, root: Path | str | None = None) -> str:
    """Enrol a project, or add a claim to one already enrolled."""
    key = str(resolve(path))
    root_key = str(resolve(root)) if root is not None else ""
    with _mutate() as rows:
        entry = rows.setdefault(key, ProjectEntry(path=key))
        entry.direct = entry.direct or direct
        entry.dev = _device(key) or entry.dev
        if root_key and root_key != key and root_key not in entry.roots:
            entry.roots.append(root_key)
    return key


def release(path: Path | str, root: Path | str) -> bool:
    """Drop one root's claim. The row survives if anything else claims it."""
    key, root_key = str(resolve(path)), str(resolve(root))
    with _mutate() as rows:
        entry = rows.get(key)
        if entry is None:
            return False
        if root_key in entry.roots:
            entry.roots.remove(root_key)
        if not entry.direct and not entry.roots:
            del rows[key]
            return True
    return False


def forget(keys: list[str]) -> tuple[list[str], list[str]]:
    """Remove the named rows. One write for the whole set.

    One write is not tidiness. `_rotate_backup` stamps to the second, so a loop
    of single-row removals overwrites its own backup inside that second, and
    what survives as the restore point is a half-pruned registry.

    Returns the rows dropped, and the members released with them.
    """
    wanted = {str(resolve(k)) for k in keys}
    dropped: list[str] = []
    released: list[str] = []
    with _mutate() as rows:
        for key in sorted(wanted & set(rows)):
            del rows[key]
            dropped.append(key)
        for key in sorted(rows):
            entry = rows[key]
            entry.roots = [r for r in entry.roots if r not in wanted]
            if not entry.direct and not entry.roots:
                del rows[key]
                released.append(key)
    return dropped, released


def mark_indexed(
    path: Path | str,
    *,
    error: str | None = None,
    counts: tuple[int, int, int] | None = None,
    capabilities: dict[str, list[str]] | None = None,
) -> None:
    """`counts` is None for a pass that wrote no graph, and the row then keeps
    what the last real pass left. Zeroing it would report a live graph as empty."""
    key = str(resolve(path))
    with _mutate() as rows:
        entry = rows.get(key)
        if entry is None:
            return
        entry.last_indexed = time.time()
        entry.last_error = error
        if counts is not None:
            entry.node_count, entry.edge_count, entry.resolved_edge_count = counts
        if capabilities is not None:
            entry.capabilities = capabilities


def fleet_digest(rows: Rows) -> str:
    """A hash of what every row *is*, not how many there are.

    A count is blind to a cancelling pair, to a disabled row, and to a dead root
    left in a live project's `roots`. No path is disclosed: the key is hashed
    with the rest.
    """
    material = sorted(
        (key, e.enabled, e.direct, tuple(sorted(e.roots)), e.last_error is not None)
        for key, e in rows.items()
    )
    return hashlib.sha256(json.dumps(material).encode()).hexdigest()[:16]


def unclaimed_stores() -> list[Path]:
    """Graph directories no row names.

    The rows and the glob come from inside one lock. Reading rows first and
    globbing after enumerates a project claimed in between as unclaimed, and the
    caller that acts on that answer deletes a graph the daemon has open.
    """
    with _held(fcntl.LOCK_SH) as rows:
        return _stale_unlocked(rows)


def _stale_unlocked(rows: Rows) -> list[Path]:
    """Graph directories no row names. Call it holding the lock, never outside.

    `.trash/` is skipped: quarantine lives under `INDEX_DIR` and no row names it,
    so counting it here would have the reaper delete its own undo on the next
    pass -- and report the deletion as reclaimed waste.
    """
    claimed = {config.index_path(e.path).parent for e in rows.values()}
    if not config.INDEX_DIR.is_dir():
        return []
    return sorted(
        p
        for p in config.INDEX_DIR.iterdir()
        if p.is_dir() and p not in claimed and p.name != quarantine.DIR_NAME
    )


def prune_unclaimed(*, force: bool = False) -> list[Path]:
    """Delete every graph directory no row names, and return what went.

    The walk and the rmtree run under one exclusive lock: a claim that lands
    between them would build the graph this deletes. `wipe` leaves the empty
    directory, which `unclaimed_stores` still counts, so a prune must rmtree.

    Two refusals on the shape of the answer, ported from the semantic engine
    after both of its fleet wipes returned a verdict that looked like this one.
    An empty registry beside a full tree of graphs is a registry that failed to
    load, not a fleet with nothing enrolled -- and `force` deliberately does not
    lift that one, because a human forcing a prune is answering the question
    "delete these", not "the registry is empty on purpose".
    """
    with _held(fcntl.LOCK_EX) as rows:
        stale = _stale_unlocked(rows)
        if not stale:
            return []
        if not rows:
            raise RuntimeError(
                f"refusing to prune {len(stale)} graph(s) against an empty registry; "
                "load projects.json before pruning"
            )
        total = len(
            [
                p
                for p in config.INDEX_DIR.iterdir()
                if p.is_dir() and p.name != quarantine.DIR_NAME
            ]
        )
        if not force and len(stale) * 2 > total:
            raise RuntimeError(
                f"refusing to prune {len(stale)} of {total} graph(s) without --force"
            )
        for path in stale:
            shutil.rmtree(path)
        return stale
