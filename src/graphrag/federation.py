"""Members, discovered by walking the symlinks under the root.

This engine declared its members until 2026-08-30, and the semantic engine
discovered them. The maintainer ruled that the two must reach the same set, and this
workspace reaches ~360 Acme repos through a symlink tree that changes
whenever a repo is added. A declared list drifts on the first such change, and
a graph nobody can query is worse than one holding a member nobody named.

A symlink is a discovery mechanism and never a key. Every path handed to the
registry, the store and the watcher is the resolved target, because inotify does
not traverse a symlink and fails silently when asked to.

`members:` survives beside the walk. It adds, so a member no symlink reaches can
still be named.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import filters, projcfg, registry

# A symlink deeper than this is a build artefact rather than a workspace layout.
MAX_DEPTH = 4

_SKIP_DIRS = frozenset({".git", ".hg", ".svn", "node_modules", "vendor", "__pycache__", ".venv"})


def _looks_like_a_project(target: Path) -> bool:
    """A directory worth its own graph, which is not the same as any directory."""
    if not target.is_dir() or filters.is_forbidden_root(target):
        return False
    return not any(part in _SKIP_DIRS for part in target.parts)


def _excluded(rel: Path, target: Path, patterns) -> bool:
    """Match against both the link and where it points.

    Both, because a pattern like `*/_worktrees/*` describes the target layout.
    Matching only the link re-admits every second checkout of a repo the root
    already reaches by another name.
    """
    return filters.matches_any(str(rel), patterns) or filters.matches_any(str(target), patterns)


def links(root: Path | str, cfg: projcfg.ProjectConfig | None = None) -> dict[Path, Path]:
    """Every member symlink under `root`, mapped to the project it resolves to.

    The link is kept beside the target because a link removed is how a member
    leaves this workspace. The target usually survives it, so no event ever
    fires there, and only the link path identifies what was lost.
    """
    base = registry.resolve(root)
    if cfg is None:
        try:
            cfg = projcfg.load(base)
        except projcfg.ConfigError:
            return {}
    found: dict[Path, Path] = {}
    for dirpath, dirnames, _ in os.walk(base, followlinks=False):
        here = Path(dirpath)
        if len(here.relative_to(base).parts) >= MAX_DEPTH:
            dirnames[:] = []
            continue
        for name in list(dirnames):
            if name in _SKIP_DIRS:
                dirnames.remove(name)
                continue
            link = here / name
            if not link.is_symlink():
                continue
            # Never descended into. The target is enrolled as a project of its
            # own, so walking through it would file its files under this root.
            dirnames.remove(name)
            try:
                target = link.resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if target == base or base in target.parents:
                continue
            if _excluded(link.relative_to(base), target, cfg.federation_exclude):
                continue
            if _looks_like_a_project(target):
                found[link] = target
    return found


def discover(root: Path | str, cfg: projcfg.ProjectConfig | None = None) -> list[Path]:
    """Every project a symlink under `root` points at, deduplicated by target."""
    return sorted(set(links(root, cfg).values()))


def _declared(base: Path, cfg: projcfg.ProjectConfig) -> list[Path]:
    out: dict[Path, None] = {}
    for entry in cfg.members:
        target = registry.resolve(base / Path(entry).expanduser())
        if target == base or not target.is_dir() or filters.is_forbidden_root(target):
            continue
        out.setdefault(target, None)
    return sorted(out)


def members_of(root: Path | str) -> list[Path]:
    """The directories this root federates: the declared set plus the walk."""
    base = registry.resolve(root)
    try:
        cfg = projcfg.load(base)
    except projcfg.ConfigError:
        # A half-read member list is worse than none, and the parse reports why.
        return []
    return sorted(set(_declared(base, cfg)) | set(discover(base, cfg)))


def expand(root: Path | str) -> list[Path]:
    """The root first, then its members. The set one question may reach."""
    base = registry.resolve(root)
    return [base, *members_of(base)]


def register(root: Path | str) -> list[Path]:
    """Claim the root directly and each member on the root's behalf.

    A member is an indirect claim, so releasing the root releases it, while a
    member enrolled directly on its own keeps its row.
    """
    base = registry.resolve(root)
    registry.claim(base, direct=True)
    members = members_of(base)
    for member in members:
        registry.claim(member, root=base)
    return members


def unregister(root: Path | str) -> list[Path]:
    """Drop this root's claim on every member it currently holds."""
    base = registry.resolve(root)
    dropped = []
    for key, entry in registry.load().items():
        if str(base) in entry.roots:
            registry.release(key, base)
            dropped.append(Path(key))
    return sorted(dropped)


def sweep(root: Path | str) -> tuple[list[Path], list[Path]]:
    """Reconcile the registry with what the root reaches now. Added, removed.

    Removing is a `release`, so it drops this root's claim and never a row that
    something else claims. That is the whole distance between this and the
    prune-by-predicate that emptied the semantic engine's fleet once.
    """
    base = registry.resolve(root)
    reachable = set(members_of(base))
    held = {Path(k) for k, e in registry.load().items() if str(base) in e.roots}
    for member in sorted(reachable - held):
        registry.claim(member, root=base)
    for member in sorted(held - reachable):
        registry.release(member, base)
    return sorted(reachable - held), sorted(held - reachable)
