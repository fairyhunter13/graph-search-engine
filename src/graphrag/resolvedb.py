"""One stored reference, scored against the graph. The rule of `resolve.py`.

The scoring is not re-derived here. The tier constants, `_SELF`, the receiver
narrowing, the global share and the ranking are imported from `resolve`, so the
two cannot drift: this module changes where an input comes from, never what a
candidate scores. `dbread` is where the inputs come from.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config, symtab
from .dbread import Context, DbRef, DbSymbol
from .resolve import (
    _SELF,
    GLOBAL_UNIQUE,
    IMPORTED_MODULE,
    IMPORTED_SYMBOL,
    SAME_CLASS,
    SAME_FILE,
    SAME_PACKAGE,
    _package,
)


@dataclass(slots=True, frozen=True)
class DbCandidate:
    symbol: DbSymbol
    confidence: float
    evidence: str


@dataclass(slots=True)
class DbResolution:
    ref: DbRef
    candidates: list[DbCandidate] = field(default_factory=list)
    external: bool = False

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def resolved(self) -> bool:
        return len(self.candidates) == 1


def receiver_modules(ref: DbRef, names: dict[str, str], modules: set[str]) -> set[str] | None:
    """`resolve._receiver_modules`, over a stored row rather than a dataclass.

    Not imported, because that one reads `extract.Reference` attributes this row
    does not have. The rule is the same and `_SELF` is shared, so the two agree
    on every case the differential test compares.
    """
    if not ref.is_member or ref.receiver in _SELF:
        return None
    if not ref.receiver:
        return set()
    out = {module for module in modules if module.rsplit(".", 1)[-1] == ref.receiver}
    base = names.get(ref.receiver)
    if base is not None:
        out.add(base)
        out.add(f"{base}.{ref.receiver}" if base else ref.receiver)
    return out


def _tier(
    ctx: Context,
    path: str,
    ref: DbRef,
    symbol: DbSymbol,
    names: dict[str, str],
    modules: set[str],
    holder: int | None,
) -> tuple[float, str] | None:
    if symbol.path == path:
        if holder is not None and ctx.parent(symbol.node_id) == holder:
            return SAME_CLASS, "same_class"
        return SAME_FILE, "same_file"

    module = symtab.module_name(symbol.path)
    if names.get(ref.name) == module:
        return IMPORTED_SYMBOL, "import"
    if module in modules:
        return IMPORTED_MODULE, "import"
    if _package(symbol.path) == _package(path):
        return SAME_PACKAGE, "package"
    return None


def _rank(candidates: list[DbCandidate]) -> list[DbCandidate]:
    best = max(c.confidence for c in candidates)
    kept = [c for c in candidates if c.confidence >= best]
    return sorted(kept, key=lambda c: (-c.confidence, c.symbol.path, c.symbol.start_byte))


def resolve_ref(ctx: Context, ref: DbRef) -> DbResolution:
    """One stored reference against the whole graph. Never forces one edge."""
    pool = ctx.pool(ref.name)
    if not pool:
        return DbResolution(ref=ref, external=True)

    names, modules = ctx.imports(ref.file_id)
    holder = ctx.enclosing_class(ctx.enclosing(ref.file_id, ref.call_site_byte))

    targets = receiver_modules(ref, names, modules)
    if targets is not None:
        pool = [s for s in pool if symtab.module_name(s.path) in targets]
        if not pool:
            return DbResolution(ref=ref, external=True)

    scoped: list[DbCandidate] = []
    for symbol in pool:
        tier = _tier(ctx, ref.path, ref, symbol, names, modules, holder)
        if tier is not None:
            scoped.append(DbCandidate(symbol=symbol, confidence=tier[0], evidence=tier[1]))
    if scoped:
        return DbResolution(ref=ref, candidates=_rank(scoped))

    share = GLOBAL_UNIQUE if len(pool) == 1 else GLOBAL_UNIQUE / len(pool)
    if share < config.CONFIDENCE_FLOOR:
        return DbResolution(ref=ref, candidates=[])
    return DbResolution(
        ref=ref,
        candidates=_rank(
            [DbCandidate(symbol=s, confidence=share, evidence="global") for s in pool]
        ),
    )
