"""Phase two: the global symbol table, built after every file is extracted.

Phase one writes nothing global, so this is where a name first becomes a set of
places it could mean. The table answers two questions and no others: what does
this name define anywhere, and which file is this module.
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from . import filters
from .extract import FileFacts

# How a language spells the thing an import names. `dotted` is Python's shape and
# was the only one until 2026-09-01: it dots a file path, while an import row
# keeps whatever the source wrote. The two agree in Python and Java and nowhere
# else, which is what `defects/module-identity-is-python-shaped.md` measured.
#
# The language comes from the path, so no caller passes one. Both halves of the
# comparison canonicalise to the same string or the import names nothing.
_SPELLING = {
    "go": "package",
    "php": "namespace",
    "typescript": "relative",
    "tsx": "relative",
    "javascript": "relative",
    "jsx": "relative",
}

# An import that writes its extension. TypeScript usually omits it, and a dotted
# name that is not one of these is part of the module: `./config.schema` stays.
_RELATIVE_SUFFIXES = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"})

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


def spelling_of(path: str) -> str:
    """Which module spelling this file's language uses."""
    return _SPELLING.get(filters.language_of(path), "dotted")


def module_name(path: str) -> str:
    """The module a path defines, in the shape an import of it names it.

    A spelling is its own namespace. `Orders.php` and `orders.ts` in one
    directory are one path with two suffixes, and without the tag they became
    one module and each file answered for the other's `Order`.
    """
    kind = spelling_of(path)
    if kind == "package":
        # Go names a directory, never a file. Every `.go` file in one directory
        # is one package, so they share a module name by design.
        return f"{kind}:{PurePosixPath(path).parent.as_posix()}"
    if kind == "namespace":
        # PSR-4 maps a namespace segment to a directory segment, and only the
        # root differs in case (`App\` under `app/`). Lowercase settles it, and
        # PHP class names are case-insensitive anyway.
        return f"{kind}:{PurePosixPath(path).with_suffix('').as_posix().lower()}"
    if kind == "relative":
        return f"{kind}:{_drop_index(PurePosixPath(path).with_suffix('')).as_posix()}"
    parts = list(PurePosixPath(path).with_suffix("").parts)
    # Never strip a path down to nothing. A file sitting directly in `src/` would
    # otherwise share the empty module name with every other such file.
    stripped = strip_source_root(parts)
    parts = stripped or parts
    if parts and parts[-1] in _PACKAGE_INIT:
        parts.pop()
    return ".".join(parts)


def _split(module: str) -> tuple[str, str, str]:
    """A module name as its spelling tag, that spelling's separator, and its body."""
    kind, tagged, body = module.partition(":")
    if tagged and kind in _SPELLING.values():
        return kind, "/", body
    return "", ".", module


def receiver_names(module: str, receiver: str) -> bool:
    """Whether a bare receiver word could name this module's last segment.

    Only the dotted spelling splits on a dot. `rsplit(".")` over
    `package:internal/billing/rates` returns the whole string, so a Go receiver
    matched nothing at all and every member call on it deferred.
    """
    kind, separator, body = _split(module)
    leaf = body.rsplit(separator, 1)[-1]
    # PSR-4 differs from its directory only in case, and `module_name` settles
    # that by lowercasing, so the receiver has to be folded to meet it.
    return leaf.lower() == receiver.lower() if kind == "namespace" else leaf == receiver


def submodule(module: str, name: str) -> str:
    """The module one level under `module`, in `module`'s own spelling."""
    kind, separator, body = _split(module)
    joined = f"{body}{separator}{name}" if body else name
    return f"{kind}:{joined}" if kind else joined


def _drop_index(path: PurePosixPath) -> PurePosixPath:
    """`dir/index.ts` is imported as `dir`, which is the only reason it exists."""
    return path.parent if path.name == "index" else path


def _package_import(module: str) -> str:
    """A Go import path, minus the repository prefix the file path never carries.

    A module path is `host/org/repo/...` and the first component is a hostname,
    so it is the one component a directory name can never be. Anything else is
    returned whole and matches nothing, which is what `fmt` should do.
    """
    parts = module.split("/")
    if len(parts) > 3 and "." in parts[0]:
        return "/".join(parts[3:])
    return module


def _relative_import(importer: str, module: str) -> str:
    """A `./x` or `../x` import as a repository-relative path.

    A bare specifier is a package from outside this tree, so it is returned
    unchanged and resolves external, which is the honest answer for it.
    """
    if not module.startswith("."):
        return module
    joined = posixpath.normpath(posixpath.join(PurePosixPath(importer).parent.as_posix(), module))
    target = PurePosixPath(joined)
    if target.suffix in _RELATIVE_SUFFIXES:
        target = target.with_suffix("")
    return _drop_index(target).as_posix()


def resolve_module(importer: str, module: str) -> str:
    """A relative import against the importing file, as an absolute module.

    A leading dot means the importer's own package, and each extra dot climbs
    one more. A module with no leading dot is returned unchanged, because an
    absolute import names the same thing from every file.

    The package comes from the importing file's directory, never from its module
    name. `pkg/mod.py` and `pkg/__init__.py` are both in `pkg`, and a rule that
    strips the last part of the module name gets the second one wrong.

    Three languages do not spell a module this way, and each returns the shape
    `module_name` gives their files. Below the branch is Python's rule, unchanged.
    """
    kind = spelling_of(importer)
    if kind == "package":
        return f"{kind}:{_package_import(module)}"
    if kind == "namespace":
        name = module.replace("\\", "/").strip("/").lower()
        return f"{kind}:{name}"
    if kind == "relative":
        return f"{kind}:{_relative_import(importer, module)}"
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
