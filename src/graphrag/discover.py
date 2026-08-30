"""Enumerating a project, and the content-hash diff that is all of staleness.

The question is "does the graph match the disk", never "how did they diverge".
That is correct after a crash, after a missed watcher event, and after a week of
downtime, and it needs no journal to be correct after any of them.

`git ls-files` first, because it already knows what a clone gets and it already
honours `.gitignore`. The walk is the fallback for a tree that is not a repo.

`ls-files` lists a gitlink as one entry and never descends into it, so a
populated submodule contributed nothing. `--recurse-submodules` is not the fix:
git refuses it beside `--others`. So the command runs once per gitlink instead.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import filters


@dataclass(slots=True, frozen=True)
class FileMeta:
    """One file as the store sees it. `sha256` decides everything."""

    rel_path: str
    size: int
    mtime: float
    sha256: str
    lang: str


@dataclass(slots=True, frozen=True)
class Diff:
    """What an index pass has to do. Empty on all three means up to date."""

    added: tuple[FileMeta, ...]
    changed: tuple[FileMeta, ...]
    removed: tuple[str, ...]

    def __bool__(self) -> bool:
        return bool(self.added or self.changed or self.removed)

    @property
    def n_touched(self) -> int:
        return len(self.added) + len(self.changed) + len(self.removed)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


GITLINK_MODE = "160000"
MAX_SUBMODULE_DEPTH = 4


def _gitlinks(root: Path) -> list[str]:
    """Relative paths of the submodule entries in `root`'s index.

    Read from the index and not from `.gitmodules`, because `.gitmodules`
    declares a submodule the tree may never have checked out.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--stage"],
            capture_output=True,
            check=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    names: list[str] = []
    for entry in out.stdout.decode().split("\0"):
        if not entry.startswith(GITLINK_MODE):
            continue
        _, _, name = entry.partition("\t")
        if name:
            names.append(name)
    return names


def _git_files(root: Path, *, depth: int = 0, seen: set[str] | None = None) -> list[Path] | None:
    """Tracked and untracked-but-not-ignored paths, or None if this is no repo.

    A populated submodule is enumerated by the same command run inside it. The
    paths come back absolute, so `enumerate_files` still derives one relative
    path against the outer root and still applies the outer excludes to it.
    """
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            check=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    found = [root / name for name in out.stdout.decode().split("\0") if name]
    if depth >= MAX_SUBMODULE_DEPTH:
        return found
    # A visited-realpath set, shared across the whole recursion: a link back to
    # an ancestor and two links to one target are both enumerated once.
    if seen is None:
        seen = set()
    seen.add(str(root.resolve()))
    for name in _gitlinks(root):
        sub = root / name
        if sub.is_symlink() or not sub.is_dir():
            continue
        real = str(sub.resolve())
        if real in seen:
            continue
        try:
            if not any(sub.iterdir()):
                continue
        except OSError:
            continue
        inner = _git_files(sub, depth=depth + 1, seen=seen)
        found.extend(inner if inner is not None else _walked_files(sub))
    return found


def _walked_files(root: Path, exclude=()) -> list[Path]:
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for item in entries:
            if item.is_symlink():
                continue
            if item.is_dir():
                # Pruned here as well as filtered below. `system/` under a
                # CodeIgniter repo holds thousands of files, and walking it to
                # discard each one costs the walk it was excluded to avoid.
                if filters.skipped_dir(item.name):
                    continue
                if exclude and filters.matches_any(str(item.relative_to(root)), exclude):
                    continue
                stack.append(item)
            else:
                found.append(item)
    return found


def enumerate_files(root: Path | str, *, exclude=(), languages=()) -> list[FileMeta]:
    """Every indexable file under `root`, as the store will hold it.

    The size comes from the stat that already happened, so a 100k-file tree is
    not stat-ed twice. Reading a file to hash it is the expensive half, and it
    happens only for a file that passed `indexable`.

    `exclude` and `languages` are the project's own two lists out of
    `.graphrag.yaml`. They are applied here, and not inside `filters.indexable`,
    because the watcher shares that predicate across every project at once.
    """
    root = Path(root).resolve()
    keep = frozenset(languages)
    candidates = _git_files(root)
    if candidates is None:
        candidates = _walked_files(root, exclude)

    metas: list[FileMeta] = []
    for path in candidates:
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            continue
        if exclude and filters.matches_any(rel, exclude):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if not path.is_file() or not filters.indexable(path, size=stat.st_size):
            continue
        lang = filters.language_of(path)
        if keep and lang not in keep:
            continue
        try:
            digest = sha256_of(path)
        except OSError:
            continue
        metas.append(
            FileMeta(
                rel_path=rel,
                size=stat.st_size,
                mtime=stat.st_mtime,
                sha256=digest,
                lang=lang,
            )
        )
    metas.sort(key=lambda m: m.rel_path)
    return metas


def diff(disk: list[FileMeta], stored: dict[str, str]) -> Diff:
    """Compare the disk against `{rel_path: sha256}` out of the store.

    `mtime` is recorded and never compared. A checkout, a restore and a touch
    all move it without moving the content, and each would then cost a full
    reparse of a tree that did not change.
    """
    on_disk = {m.rel_path: m for m in disk}
    added = tuple(m for p, m in on_disk.items() if p not in stored)
    changed = tuple(m for p, m in on_disk.items() if p in stored and stored[p] != m.sha256)
    removed = tuple(sorted(p for p in stored if p not in on_disk))
    return Diff(added=added, changed=changed, removed=removed)


def languages(disk: list[FileMeta]) -> dict[str, int]:
    """File count per language, for the capability report `doctor` prints."""
    counts: dict[str, int] = {}
    for meta in disk:
        counts[meta.lang] = counts.get(meta.lang, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
