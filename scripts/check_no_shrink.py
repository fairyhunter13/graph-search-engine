"""Augment, never shrink. Run `okf check -against` and grade what it reports.

`-Werror` is the obvious gate and it is wrong here. `okf verify -stamp` moves
the `at` of an existing event, so every re-stamp reports the old event as
dropped, and `-Werror` would block the next push in every repo that stamps.
So a lost verification event is a finding only where its actor is gone from
the file as well.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

WARNING = re.compile(r"^(?P<path>[^:]+): warning: (?P<msg>.*)$")
EVENT = re.compile(r'^verification event "(?P<actor>\S+) \S+" was dropped$')
SHRINK = (" was dropped or reordered", " was dropped: provenance only accumulates")


def _actor_survives(path: Path, actor: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    head = text.split("\n---", 2)[0] if text.startswith("---") else text
    return any(f"by: {quote}{actor}{quote}" in head for quote in ("", "'", '"'))


def findings(output: str, root: Path) -> list[str]:
    """Every reported shrink that a re-stamp does not explain."""
    out = []
    for line in output.splitlines():
        hit = WARNING.match(line.strip())
        if hit is None:
            continue
        msg = hit.group("msg")
        event = EVENT.match(msg)
        if event is not None:
            if not _actor_survives(root / hit.group("path"), event.group("actor")):
                out.append(line.strip())
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
    hits = findings(run.stdout + run.stderr, Path(repo))
    for hit in hits:
        print(hit)
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
