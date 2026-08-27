"""Augment, never shrink. Run `okf check -against` and grade what it reports.

`-Werror` is the obvious gate and it is wrong here. `okf verify -stamp` moves
the `at` of an existing event, so every re-stamp reports the old event as
dropped, and `-Werror` would block the next push in every repo that stamps.
So a lost verification event is a finding only where its actor is gone from
the file as well.

`okf check` names a dropped source by its resource string, so correcting a
broken path reads as a drop. The `id` is the stable handle, so a source is a
finding only where the `id` that carried it is gone from the file as well.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

WARNING = re.compile(r"^(?P<path>[^:]+): warning: (?P<msg>.*)$")
EVENT = re.compile(r'^verification event "(?P<actor>\S+) \S+" was dropped$')
SOURCE = re.compile(r'^source "(?P<resource>.+)" was dropped: provenance only accumulates$')
SHRINK = (" was dropped or reordered", " was dropped: provenance only accumulates")
ID = re.compile(r"^\s*-?\s*id:\s*(\S+)\s*$")
RESOURCE = re.compile(r"^\s*-?\s*resource:\s*(.+?)\s*$")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _show(base: str, root: Path, path: str) -> str:
    """The file as the base ref holds it, or empty where the ref does not carry it."""
    try:
        rel = (root / path).resolve().relative_to(root.resolve())
    except ValueError:
        return ""
    run = subprocess.run(
        ["git", "-C", str(root), "show", f"{base}:{rel.as_posix()}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return run.stdout if run.returncode == 0 else ""


def _actor_survives(path: Path, actor: str) -> bool:
    text = _read(path)
    head = text.split("\n---", 2)[0] if text.startswith("---") else text
    return any(f"by: {quote}{actor}{quote}" in head for quote in ("", "'", '"'))


def _sources(text: str) -> list[tuple[str, str]]:
    """Every `sources` entry as its id and its resource, either order, ids only."""
    head = text.split("\n---", 2)[0] if text.startswith("---") else text
    out: list[tuple[str, str]] = []
    ident = ""
    for line in head.splitlines():
        got_id, got_resource = ID.match(line), RESOURCE.match(line)
        if got_id is not None:
            # A new id opens an entry. The top-level `resource` field sits before
            # any id, so an open entry is the only thing a resource line pairs with.
            ident = got_id.group(1)
        elif got_resource is not None and ident:
            out.append((ident, got_resource.group(1)))
            ident = ""
    return out


def _id_survives(old: str, new: str, resource: str) -> bool:
    """The id that carried this resource is still in the file, under any resource."""
    carriers = {i for i, r in _sources(old) if r == resource}
    return bool(carriers) and carriers <= {i for i, _ in _sources(new)}


def findings(output: str, root: Path, base: str = "") -> list[str]:
    """Every reported shrink that a re-stamp or a corrected citation does not explain."""
    out = []
    for line in output.splitlines():
        hit = WARNING.match(line.strip())
        if hit is None:
            continue
        msg, path = hit.group("msg"), hit.group("path")
        event = EVENT.match(msg)
        if event is not None:
            if not _actor_survives(root / path, event.group("actor")):
                out.append(line.strip())
            continue
        source = SOURCE.match(msg)
        if source is not None and base:
            old = _show(base, root, path)
            new = _read(root / path)
            if old and _id_survives(old, new, source.group("resource")):
                continue
        if any(msg.endswith(tail) for tail in SHRINK):
            out.append(line.strip())
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: check_no_shrink.py <base-ref> <bundle>", file=sys.stderr)
        return 2
    base, bundle = argv[1], Path(argv[2]).resolve()
    repo = subprocess.run(
        ["git", "-C", str(bundle), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    run = subprocess.run(
        ["okf", "check", "-against", base, str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    hits = findings(run.stdout + run.stderr, Path(repo), base)
    for hit in hits:
        print(hit)
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
