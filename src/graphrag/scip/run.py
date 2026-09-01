"""What each SCIP indexer can be trusted for, and how one is invoked.

Capability is per indexer, exactly as it is per capture in tree-sitter. Five of
the ten live indexers leave `SymbolInformation.kind` at 0, so `kind` is never a
field to depend on: 0 means keep the tree-sitter kind, and it never means
`Unspecified` as a real answer. `rust-analyzer` emits no relationships at all,
so a Rust trait implementation comes from tree-sitter or from nowhere.

Exit status proves nothing here. `scip-python` retries a failed analysis a
hundred times, drops the file, writes the index and exits 0
(`sourcegraph/scip-python#221`), so `ingest.coverage` decides, not the code.

Every one of these needs a resolved build that tree-sitter does not, and that
asymmetry is the whole reason this tier is an overlay. So a table entry with no
command is not a gap: it means the operator runs their own build and hands the
index over, which is the only honest default for a tool needing a Gradle run.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

OUTPUT_NAME = "index.scip"


@dataclass(frozen=True, slots=True)
class Indexer:
    """One tool, keyed by the `tool_info.name` its own index carries."""

    name: str
    languages: tuple[str, ...]
    # Whether `SymbolInformation.kind` is populated. False means 0 everywhere,
    # and 0 must never overwrite a kind tree-sitter already found.
    sets_kind: bool
    # Whether `Relationship` is emitted, which is where `is_implementation`
    # lives. This tier's single highest-value output, and the one an inheritance
    # query cannot get syntactically for Python or Go.
    emits_relationships: bool
    # Argv, with the output path appended. Empty means the operator runs the
    # build themselves, because no flag set makes a Gradle project index itself.
    command: tuple[str, ...] = ()
    # The filename that declares an independent build root, where a repository
    # can hold several. Empty means one invocation covers the whole project.
    unit: str = ""
    # A path inside a build unit whose presence says the dependencies are
    # resolved. Empty where they resolve outside the tree, as Go's module cache
    # does, so the tree cannot answer and `readiness` must not claim it can.
    deps: str = ""


INDEXERS: dict[str, Indexer] = {
    i.name: i
    for i in (
        Indexer("scip-python", ("python",), False, True, ("scip-python", "index", "--output")),
        Indexer(
            "scip-typescript",
            ("typescript", "javascript"),
            False,
            True,
            ("scip-typescript", "index", "--output"),
            "tsconfig.json",
            "node_modules",
        ),
        Indexer("scip-go", ("go",), True, True, ("scip-go", "index", "--output"), "go.mod"),
        Indexer("scip-java", ("java", "scala", "kotlin"), True, True),
        Indexer("scip-clang", ("c", "cpp"), False, True),
        Indexer("scip-ruby", ("ruby",), False, True),
        Indexer("scip-dart", ("dart",), True, True),
        Indexer("scip-php", ("php",), False, True, deps="vendor/autoload.php"),
        Indexer("rust-analyzer", ("rust",), True, False),
    )
}


# A build unit never lives under one of these. `vendor` and `node_modules` hold
# another project's modules, and indexing them attributes their files to this
# repository.
SKIP = frozenset({"vendor", "node_modules", "testdata"})


class RunError(RuntimeError):
    """An indexer that could not be run, named."""


def indexer(name: str) -> Indexer:
    """The capability row for a tool name, or an error naming the known set."""
    got = INDEXERS.get(name)
    if got is None:
        raise RunError(
            f"{name!r} is not a known SCIP indexer. Known: {', '.join(sorted(INDEXERS))}"
        )
    return got


def units(name: str, root: Path | str) -> list[str]:
    """Every build root under a project, as posix prefixes relative to it.

    An indexer resolves the build it stands in and no other, so a repository
    holding several is several invocations. One measured Go monorepo carries
    eight `go.mod` files and 2,010 of its 2,012 Go files sit outside the root
    one, which is why one pass at the top covered 0% and was correctly refused.

    The root itself is always a prefix, so an indexer with no unit marker, and
    a project with no marker in it, both return the single empty prefix.
    """
    got = indexer(name)
    root = Path(root).resolve()
    if not got.unit:
        return [""]
    found = []
    for path in root.rglob(got.unit):
        rel = path.parent.relative_to(root)
        if any(part in SKIP or part.startswith(".") for part in rel.parts):
            continue
        found.append(rel.as_posix() if rel.parts else "")
    return sorted(found) or [""]


def for_language(lang: str) -> list[Indexer]:
    return [i for i in INDEXERS.values() if lang in i.languages]


TIERS = ("ready", "installable", "unconfigured", "manual", "absent")


def _standing(got: Indexer, root: Path) -> dict[str, object]:
    """One indexer's standing over one project: a tier, and the evidence for it.

    `manual` is decided before `absent` because an indexer with no argv has no
    program to look for. That is not a gap — it means the operator runs their
    own build and hands the index over.

    `unconfigured` is the tier a fallback would otherwise hide. `units` answers
    `[""]` both for an indexer needing no marker and for a project holding none,
    which is right for `overlay` — try the root — and wrong for a report, where
    it reads as a build unit that is not there.

    An indexer whose dependencies resolve outside the tree reports `deps: ""`
    and cannot reach `ready` from a filesystem read, so it stands at
    `installable`. Its install command is idempotent, and running it is what
    settles a question the tree cannot answer.
    """
    prefixes = units(got.name, root)
    marked = not got.unit or prefixes != [""] or (root / got.unit).exists()
    missing = [p for p in prefixes if got.deps and not (root / p / got.deps).exists()]
    if not got.command:
        tier = "manual"
    elif shutil.which(got.command[0]) is None:
        tier = "absent"
    elif not marked:
        tier = "unconfigured"
    elif got.deps and not missing:
        tier = "ready"
    else:
        tier = "installable"
    return {
        "indexer": got.name,
        "tier": tier,
        "units": prefixes if marked else [],
        "deps": got.deps,
        "unresolved": missing,
    }


def readiness(root: Path | str, languages: Iterable[str]) -> list[dict[str, object]]:
    """Every indexer that would serve a language this project holds.

    A report and never an action: it reads `PATH` and the tree, installs
    nothing and changes no default. An indexer is listed only where the project
    holds one of its languages, so the same rule that keeps `overlay` from
    starting a Go build in a PHP repository decides what appears here.
    """
    root = Path(root).resolve()
    want = set(languages)
    return [_standing(got, root) for got in INDEXERS.values() if want.intersection(got.languages)]


def run(name: str, root: Path | str, out: Path | str = "", timeout: float = 1800.0) -> Path:
    """Invoke one indexer over a project, and return the index it wrote.

    The return is the file, never the exit code. A tool that exits 0 and writes
    a collapsed index is the documented failure, and `ingest.coverage` is what
    catches it, so nothing here treats 0 as evidence of anything.
    """
    got = indexer(name)
    root = Path(root).resolve()
    out = Path(out) if out else root / OUTPUT_NAME
    if not got.command:
        raise RunError(
            f"{name} needs the project's own build, so graphrag does not invoke it. "
            f"Run it yourself and point the overlay at the index it writes."
        )
    try:
        subprocess.run(
            [*got.command, str(out)], cwd=root, capture_output=True, timeout=timeout, check=False
        )
    except FileNotFoundError as exc:
        raise RunError(f"{got.command[0]} is not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RunError(f"{name} did not finish within {timeout:.0f}s") from exc
    if not out.exists():
        raise RunError(f"{name} wrote no index at {out}")
    return out
