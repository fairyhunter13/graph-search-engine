"""Members, declared in `.graphrag.yaml` and expanded exactly one level.

The semantic engine discovers members by walking symlinks under the root. This
one does not, and the difference is deliberate: a graph answers a question about
a named symbol, so a member that arrives by accident adds candidate definitions
the operator never asked for and cannot see. Declaring the set makes the blast
radius of a change something a person chose.

One level, never transitive. A member's own members belong to that member, and
following them turns a two-repo workspace into whatever the far end declares.
"""

from __future__ import annotations

from pathlib import Path

from . import filters, projcfg, registry


def members_of(root: Path | str) -> list[Path]:
    """The directories this root federates, resolved and deduplicated.

    A declared path that is absent is dropped rather than raised. A member on an
    unmounted disk is absent, not wrong, and the registry rule that nothing is
    pruned for a missing path applies to the declaration too.
    """
    base = registry.resolve(root)
    try:
        cfg = projcfg.load(base)
    except projcfg.ConfigError:
        # A config that cannot be obeyed is reported where it is parsed. Here it
        # means no members, because a half-read member list is worse than none.
        return []
    out: dict[Path, None] = {}
    for entry in cfg.members:
        target = registry.resolve(base / Path(entry).expanduser())
        if target == base or not target.is_dir() or filters.is_forbidden_root(target):
            continue
        out.setdefault(target, None)
    return sorted(out)


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
    """Reconcile the registry with the declaration. Returns added and removed.

    The config is the truth, so a member deleted from it loses this root's claim
    on the next sweep. Nothing else changes, which is what makes the answer
    stable enough for the watcher to re-arm on.
    """
    base = registry.resolve(root)
    declared = set(members_of(base))
    held = {Path(k) for k, e in registry.load().items() if str(base) in e.roots}
    for member in sorted(declared - held):
        registry.claim(member, root=base)
    for member in sorted(held - declared):
        registry.release(member, base)
    return sorted(declared - held), sorted(held - declared)
