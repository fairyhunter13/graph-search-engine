"""Resolve a project's dependencies so a SCIP indexer can run, and nothing else.

Separate from `run.py` deliberately, and the separation is the point. `run`
invokes an indexer and installs nothing; this installs and indexes nothing. A
package manager executes code it just downloaded, so the surface that starts one
is not a surface an index pass can reach — this one is invoked by hand, per root:

    python -m graphrag.scip.deps <root>

It resolves only what `run.readiness` calls `installable`. A `manual` indexer
needs the project's own build and an `absent` one is not installed, so resolving
for either buys a run that still cannot happen.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from .. import config, store
from . import run

# A package manager that runs a downloaded package's lifecycle scripts. Resolving
# a dependency must not execute it, so each of these carries a suppressing flag
# or it is refused. `go mod download` is absent because it runs no module's code.
SCRIPTED = frozenset({"npm", "pnpm", "yarn", "bun"})
SUPPRESSORS = frozenset({"--ignore-scripts"})

# The first marker present in a build unit decides the command.
PLANS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "scip-typescript": (
        ("pnpm-lock.yaml", ("pnpm", "install", "--frozen-lockfile", "--ignore-scripts")),
        ("package-lock.json", ("npm", "ci", "--ignore-scripts")),
    ),
    "scip-go": (("go.mod", ("go", "mod", "download")),),
}

LEDGER = "deps.jsonl"


class RefusedError(RuntimeError):
    """A command this helper will not run, named with the reason."""


def check(argv: tuple[str, ...]) -> str:
    """Why this command is refused, or an empty string.

    The whole guard, and it grades the command rather than the table. A plan is
    data and data drifts, so the flag is asserted where the command is chosen
    and never where it was written.
    """
    if not argv:
        return "an empty command"
    if argv[0] in SCRIPTED and not SUPPRESSORS.intersection(argv):
        return (
            f"{argv[0]} runs a downloaded package's lifecycle scripts, and "
            f"{' '.join(argv)} carries none of {', '.join(sorted(SUPPRESSORS))}"
        )
    return ""


def plan(name: str, where: Path) -> tuple[str, ...]:
    """The checked command that resolves one build unit."""
    for marker, argv in PLANS.get(name, ()):
        if not (where / marker).exists():
            continue
        reason = check(argv)
        if reason:
            raise RefusedError(f"{name} in {where}: {reason}")
        return argv
    raise RefusedError(f"{name} has no dependency plan that fits {where}")


def _languages(root: Path) -> frozenset[str]:
    path = config.index_path(root)
    if not path.exists():
        return frozenset()
    conn = store.connect(path, create=False)
    try:
        return frozenset(row[0] for row in conn.execute("SELECT DISTINCT lang FROM files"))
    finally:
        conn.close()


def _record(root: Path, entry: dict[str, object]) -> None:
    """Append to the ledger beside the graph, never inside the project.

    The engine indexes trees it does not own, so what it did to one belongs
    where its graph does.
    """
    path = config.index_path(root).parent / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def resolve(root: Path | str, timeout: float = 1800.0) -> list[dict[str, object]]:
    """Run the dependency plan for every installable unit, and record each run.

    A refusal is an outcome and never an exception, exactly as it is in
    `overlay`: one unit with no plan must not cost the others theirs.
    """
    root = Path(root).resolve()
    done: list[dict[str, object]] = []
    for standing in run.readiness(root, _languages(root)):
        if standing["tier"] != "installable":
            continue
        for prefix in standing["units"]:
            where = root / prefix if prefix else root
            entry: dict[str, object] = {
                "at": time.time(),
                "indexer": standing["indexer"],
                "unit": prefix,
            }
            try:
                argv = plan(str(standing["indexer"]), where)
            except RefusedError as exc:
                entry["refused"] = str(exc)
            else:
                got = subprocess.run(argv, cwd=where, capture_output=True, timeout=timeout)
                entry["command"] = list(argv)
                entry["returncode"] = got.returncode
                entry["stderr"] = got.stderr.decode("utf-8", "replace")[-2000:]
            _record(root, entry)
            done.append(entry)
    return done


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m graphrag.scip.deps <root>", file=sys.stderr)
        return 2
    json.dump(resolve(args[0]), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
