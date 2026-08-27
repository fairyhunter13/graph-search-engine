"""Import-scoped, confidence-ranked resolution. Never forces a single edge.

Measured 2026-08-27 on CPython `v3.12.7`, 755 files of `Lib` with the test tree
excluded, 53853 call sites. Global name matching gives 10.86 candidate files per
site and 54.5% of sites are ambiguous. Import scoping gives 1.49 and 17.7%, a
collapse of 7.3 times. `T-07` is that measurement and it asserts the ratio, not
the two numbers: a corpus at another tag moves both arms together.

Every survivor is emitted as its own edge with its confidence and the size of
the set it came from. A name defined nowhere becomes an external node, and is
never forced onto an in-repo homonym.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from . import config
from .extract import Reference
from .symtab import Symbol, SymbolTable, imported_modules, imported_names

# The scored tiers, highest first. `evidence` is what the answer prints, so a
# reader can tell a fact from a guess without reading this file.
SAME_CLASS = 0.95
SAME_FILE = 0.90
IMPORTED_SYMBOL = 0.85
IMPORTED_MODULE = 0.70
SAME_PACKAGE = 0.40
GLOBAL_UNIQUE = 0.30


@dataclass(slots=True)
class Candidate:
    symbol: Symbol
    confidence: float
    evidence: str


@dataclass(slots=True)
class Resolution:
    reference: Reference
    candidates: list[Candidate]
    external: bool = False

    @property
    def resolved(self) -> bool:
        return len(self.candidates) == 1

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)


def _enclosing_class(table: SymbolTable, path: str, scope: int | None) -> int | None:
    """The class a call site sits in, or None. Walks the containment chain."""
    facts = table.files.get(path)
    if facts is None or scope is None:
        return None
    seen: set[int] = set()
    cursor: int | None = scope
    while cursor is not None and cursor not in seen:
        seen.add(cursor)
        if facts.definitions[cursor].kind == "class":
            return cursor
        cursor = facts.definitions[cursor].parent
    return None


def _package(path: str) -> str:
    return str(PurePosixPath(path).parent)


def _tier(
    table: SymbolTable,
    path: str,
    ref: Reference,
    symbol: Symbol,
    names: dict[str, str],
    modules: set[str],
    holder: int | None,
) -> tuple[float, str] | None:
    """The one tier a candidate earns, or None where it earns none."""
    if symbol.path == path:
        if holder is not None and symbol.parent == holder:
            return SAME_CLASS, "same_class"
        return SAME_FILE, "same_file"

    module = table.path_module.get(symbol.path, "")
    if names.get(ref.name) == module:
        return IMPORTED_SYMBOL, "import"
    if module in modules:
        return IMPORTED_MODULE, "import"
    if _package(symbol.path) == _package(path):
        return SAME_PACKAGE, "package"
    return None


def resolve_reference(table: SymbolTable, path: str, ref: Reference) -> Resolution:
    """One reference against the whole table. The candidate set is never forced."""
    pool = table.defines(ref.name)
    if not pool:
        return Resolution(reference=ref, candidates=[], external=True)

    names = imported_names(table, path)
    modules = imported_modules(table, path)
    holder = _enclosing_class(table, path, ref.scope)

    scoped: list[Candidate] = []
    for symbol in pool:
        tier = _tier(table, path, ref, symbol, names, modules, holder)
        if tier is not None:
            scoped.append(Candidate(symbol=symbol, confidence=tier[0], evidence=tier[1]))

    if scoped:
        return Resolution(reference=ref, candidates=_rank(scoped))

    # Nothing in scope, so the whole repo is the candidate set and the score says
    # so. A single global match is a real answer; twenty is a ranked guess.
    share = GLOBAL_UNIQUE if len(pool) == 1 else GLOBAL_UNIQUE / len(pool)
    if share < config.CONFIDENCE_FLOOR:
        return Resolution(reference=ref, candidates=[])
    return Resolution(
        reference=ref,
        candidates=_rank([Candidate(symbol=s, confidence=share, evidence="global") for s in pool]),
    )


def _rank(candidates: list[Candidate]) -> list[Candidate]:
    """Best first, and a tie breaks on the path so two runs agree.

    Only the best tier survives. A candidate reachable through an import and a
    worse candidate reachable only because the repo happens to hold the name are
    not two answers to rank, and keeping the second inflates every count.
    """
    best = max(c.confidence for c in candidates)
    kept = [c for c in candidates if c.confidence >= best]
    return sorted(kept, key=lambda c: (-c.confidence, c.symbol.path, c.symbol.index))


def resolve_file(table: SymbolTable, path: str) -> list[Resolution]:
    facts = table.files.get(path)
    if facts is None:
        return []
    return [resolve_reference(table, path, ref) for ref in facts.references]


def mean_candidates(
    table: SymbolTable, scoped: bool, unit: str = "file"
) -> tuple[float, float, int]:
    """The `T-07` measurement, one arm per call, in one pass over the table.

    Returns the mean candidate count, the ambiguous share, and the number of call
    sites that contributed. A site whose name is defined nowhere in the repo is
    excluded from both arms: it is an external node under either rule, so
    counting it would move both means by the same amount and prove nothing.

    `unit` is `file` or `definition`, and the two are different questions. The
    design claim is about candidate *files*, because a caller reading an answer
    opens a file. `definition` is what an edge count sees, and it is higher
    wherever one file defines a name more than once.
    """
    if unit not in ("file", "definition"):
        raise ValueError(f"unit must be 'file' or 'definition', not {unit!r}")

    total = ambiguous = sites = 0
    for path, facts in table.files.items():
        for ref in facts.references:
            pool = table.defines(ref.name)
            if not pool:
                continue
            found = (
                [c.symbol for c in resolve_reference(table, path, ref).candidates]
                if scoped
                else pool
            )
            n = len({s.path for s in found}) if unit == "file" else len(found)
            if n == 0:
                continue
            sites += 1
            total += n
            ambiguous += 1 if n > 1 else 0
    if sites == 0:
        return 0.0, 0.0, 0
    return total / sites, ambiguous / sites, sites
