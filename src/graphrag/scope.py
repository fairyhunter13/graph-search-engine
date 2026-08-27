"""Containment, not authorization.

Nothing here decides what a caller is allowed to read. It decides which enrolled
project a path belongs to, so an answer files under the root that owns it. A
path outside every root is not a permission failure, it is a question about a
project nobody enrolled, and the reply says so rather than picking the nearest.
"""

from __future__ import annotations

from pathlib import Path

from . import federation, registry


def contains(root: Path | str, path: Path | str) -> bool:
    """Whether a path lies inside a root, both resolved first.

    Resolving both sides is the whole check. A symlink into a root is inside it
    and a relative path that climbs out of one is not, and only the resolved
    forms show either.
    """
    base, target = registry.resolve(root), registry.resolve(path)
    return target == base or base in target.parents


def within(root: Path | str, path: Path | str) -> bool:
    """Whether a path lies inside the root or one of its declared members."""
    return any(contains(member, path) for member in federation.expand(root))


def owner(path: Path | str) -> Path | None:
    """The enrolled project that owns a path, deepest root first.

    Deepest wins because a project enrolled inside another is the more specific
    answer, and filing its files under the outer root loses that distinction.
    """
    target = registry.resolve(path)
    roots = [Path(key) for key in registry.load()]
    inside = [root for root in roots if target == root or root in target.parents]
    return max(inside, key=lambda root: len(root.parts)) if inside else None


def refuse(root: Path | str, path: Path | str) -> str:
    """An error naming the reachable set, or an empty string where it is in it."""
    if within(root, path):
        return ""
    reachable = ", ".join(str(member) for member in federation.expand(root))
    return f"{registry.resolve(path)} is outside this workspace, which reaches {reachable}"
