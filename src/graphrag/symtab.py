"""Phase two: the global symbol table, built after every file is extracted.

Phase one writes nothing global, so this is where a name first becomes a set of
places it could mean. The table answers two questions and no others: what does
this name define anywhere, and which file is this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath

from .extract import FileFacts

# A package directory is named by its initialiser, so the module name drops the
# last part. Without this `pkg/__init__.py` reads as the module `pkg.__init__`
# and no `from . import x` ever resolves.
_PACKAGE_INIT = ("__init__", "index", "mod")

# Build-tool directories that carry no part of the name an import writes. Maven
# and Gradle put `com.acme.Foo` at `src/main/java/com/acme/Foo.java`, so the
# derived name is `src.main.java.com.acme.Foo` and matches no import ever
# written. Longest first, because `src/main/java` must beat `src`.
_SOURCE_ROOTS: tuple[tuple[str, ...], ...] = tuple(
    tuple(prefix.split("/"))
    for prefix in (
        "src/main/java",
        "src/main/kotlin",
        "src/main/scala",
        "src/main/resources",
        "src/test/java",
        "src/test/kotlin",
        "src/test/scala",
        "app/src/main/java",
        "app/src/main/kotlin",
        "src",
        "lib",
    )
)


@dataclass(slots=True, frozen=True)
class Symbol:
    path: str
    index: int
    kind: str
    name: str
    qualified_name: str
    parent: int | None = None


@dataclass(slots=True)
class SymbolTable:
    files: dict[str, FileFacts] = field(default_factory=dict)
    by_name: dict[str, list[Symbol]] = field(default_factory=dict)
    path_module: dict[str, str] = field(default_factory=dict)

    def defines(self, name: str) -> list[Symbol]:
        """Every definition of a name, anywhere. The unscoped candidate set."""
        return self.by_name.get(name, [])

    def symbols_in(self, path: str) -> list[Symbol]:
        facts = self.files.get(path)
        if facts is None:
            return []
        return [_symbol(path, i, d) for i, d in enumerate(facts.definitions)]


def strip_source_root(parts: list[str]) -> list[str]:
    """Drop a build-tool prefix, longest match first."""
    for root in sorted(_SOURCE_ROOTS, key=len, reverse=True):
        if tuple(parts[: len(root)]) == root:
            return parts[len(root) :]
    return parts


def module_name(path: str) -> str:
    """The dotted module a path defines, in the shape an import names it."""
    parts = list(PurePosixPath(path).with_suffix("").parts)
    # Never strip a path down to nothing. A file sitting directly in `src/` would
    # otherwise share the empty module name with every other such file.
    stripped = strip_source_root(parts)
    parts = stripped or parts
    if parts and parts[-1] in _PACKAGE_INIT:
        parts.pop()
    return ".".join(parts)


def resolve_module(importer: str, module: str) -> str:
    """A relative import against the importing file, as an absolute module.

    A leading dot means the importer's own package, and each extra dot climbs
    one more. A module with no leading dot is returned unchanged, because an
    absolute import names the same thing from every file.

    The package comes from the importing file's directory, never from its module
    name. `pkg/mod.py` and `pkg/__init__.py` are both in `pkg`, and a rule that
    strips the last part of the module name gets the second one wrong.
    """
    if not module.startswith("."):
        return module
    depth = len(module) - len(module.lstrip("."))
    parts = strip_source_root(list(PurePosixPath(importer).parent.parts))
    base = parts[: max(0, len(parts) - depth + 1)]
    tail = module.lstrip(".")
    return ".".join([p for p in base if p not in (".", "")] + ([tail] if tail else []))


def build(facts_by_path: dict[str, FileFacts]) -> SymbolTable:
    """One pass over every extracted file. No parsing happens here."""
    table = SymbolTable(files=dict(facts_by_path))
    for path, facts in facts_by_path.items():
        table.path_module[path] = module_name(path)
        for i, definition in enumerate(facts.definitions):
            table.by_name.setdefault(definition.name, []).append(_symbol(path, i, definition))
    return table


def _symbol(path: str, index: int, definition) -> Symbol:
    return Symbol(
        path=path,
        index=index,
        kind=definition.kind,
        name=definition.name,
        qualified_name=definition.qualified_name,
        parent=definition.parent,
    )


def names_from_imports(path: str, rows) -> dict[str, str]:
    """The names one file imported, each mapped to the module it came from.

    An alias is the name the body actually uses, so it wins over the symbol.
    """
    out: dict[str, str] = {}
    for row in rows:
        module = resolve_module(path, row.module)
        if row.symbol:
            out[row.alias or row.symbol] = module
        elif row.alias:
            out[row.alias] = module
    return out


def imported_names(table: SymbolTable, path: str) -> dict[str, str]:
    facts = table.files.get(path)
    return names_from_imports(path, facts.imports) if facts else {}


def imported_modules(table: SymbolTable, path: str) -> set[str]:
    """Every module this file pulled in, whether by name or whole."""
    facts = table.files.get(path)
    if facts is None:
        return set()
    return {resolve_module(path, row.module) for row in facts.imports}
