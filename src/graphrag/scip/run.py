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

import subprocess
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
        ),
        Indexer("scip-go", ("go",), True, True, ("scip-go", "--output")),
        Indexer("scip-java", ("java", "scala", "kotlin"), True, True),
        Indexer("scip-clang", ("c", "cpp"), False, True),
        Indexer("scip-ruby", ("ruby",), False, True),
        Indexer("scip-dart", ("dart",), True, True),
        Indexer("scip-php", ("php",), False, True),
        Indexer("rust-analyzer", ("rust",), True, False),
    )
}


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


def for_language(lang: str) -> list[Indexer]:
    return [i for i in INDEXERS.values() if lang in i.languages]


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
