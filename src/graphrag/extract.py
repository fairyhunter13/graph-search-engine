"""Per-file parse to dataclasses. Writes nothing global.

Scope and method-ness are decided by byte containment, not by asking the AST
what a class node is called. Every grammar spells that differently, and Python's
`tags.scm` emits `@definition.function` for a method with no `@definition.method`
at all, so containment is the only rule that holds across 68 grammars.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache

import tree_sitter as ts
from tree_sitter_language_pack import get_language

from . import grammars, queries

# The byte that precedes an identifier in a member call. `expr.method()` is about
# 43% of call sites.
_MEMBER_BYTES = (b".", b">", b":")

# What a receiver name is spelled with. `$` is here for PHP, where `$this` is
# the receiver and dropping the sigil would make it a different name.
_IDENT_BYTES = frozenset(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$")


@dataclass(slots=True)
class Definition:
    kind: str
    name: str
    start_byte: int  # the identifier token range, and the SCIP upsert key
    end_byte: int
    start_line: int
    end_line: int
    body_end_byte: int
    parent: int | None = None
    qualified_name: str = ""


@dataclass(slots=True)
class Reference:
    kind: str
    name: str
    call_site_byte: int
    line: int
    scope: int | None = None
    is_member: bool = False
    receiver: str = ""


@dataclass(slots=True)
class Import:
    module: str
    symbol: str = ""
    alias: str = ""
    line: int = 0


@dataclass(slots=True)
class FileFacts:
    lang: str
    n_lines: int = 0
    definitions: list[Definition] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    imports: list[Import] = field(default_factory=list)
    error: str = ""
    # Why this file answers less than its language promises, from `store.REASONS`.
    # `error` carries the message and this carries the class; a reader branches on
    # one and prints the other.
    reason: str = ""


@cache
def _compiled(lang: str, source: str):
    """One `Query` per language, not one per file.

    Compiling costs 3.82 ms against 0.58 ms to parse the file, and the same two
    query texts are compiled for every file in the tree.
    """
    return ts.Query(get_language(lang), source)


def _run(facts: FileFacts, lang: str, source: str, tree) -> list:
    """Run a query, returning matches. A broken query is not fatal.

    The cursor is the mutable half and is built per call; the query is immutable
    once compiled and is shared.

    It leaves a mark rather than only an empty list. A swallowed query error
    returned `[]`, which is byte-identical in the store to a file that parsed
    clean and defined nothing.
    """
    if not source:
        return []
    try:
        return ts.QueryCursor(_compiled(lang, source)).matches(tree.root_node)
    except Exception:
        facts.reason = "query_failed"
        return []


def _text(data: bytes, node) -> str:
    return data[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _enclosing(defs: list[Definition], byte: int) -> int | None:
    """The innermost definition whose body holds this byte."""
    best, best_span = None, None
    for i, d in enumerate(defs):
        if d.start_byte <= byte < d.body_end_byte:
            span = d.body_end_byte - d.start_byte
            if best_span is None or span < best_span:
                best, best_span = i, span
    return best


def _link(defs: list[Definition]) -> None:
    """Fill `parent`, promote a contained function to a method, and qualify."""
    for i, d in enumerate(defs):
        outer, outer_span = None, None
        for j, other in enumerate(defs):
            if i == j or not (other.start_byte <= d.start_byte < other.body_end_byte):
                continue
            span = other.body_end_byte - other.start_byte
            if outer_span is None or span < outer_span:
                outer, outer_span = j, span
        d.parent = outer
        if outer is not None and d.kind == "function" and defs[outer].kind == "class":
            d.kind = "method"

    for d in defs:
        chain, seen = [d.name], set()
        cursor = d.parent
        while cursor is not None and cursor not in seen:
            seen.add(cursor)
            chain.append(defs[cursor].name)
            cursor = defs[cursor].parent
        d.qualified_name = ".".join(reversed(chain))


def _member(data: bytes, node) -> tuple[bool, str]:
    """The separator before an identifier, and the receiver that precedes it.

    The receiver is what tells `registry.load()` from `yaml.load()`. Discarding
    it made the two one name, and `D-18` measured what that costs.
    """
    i = node.start_byte - 1
    while i >= 0 and data[i : i + 1].isspace():
        i -= 1
    if i < 0 or data[i : i + 1] not in _MEMBER_BYTES:
        return False, ""
    # `->` and `::` are two bytes, and the receiver sits before both of them.
    if data[i : i + 1] in (b">", b":") and i > 0 and data[i - 1 : i] in (b"-", b":"):
        i -= 1
    i -= 1
    while i >= 0 and data[i : i + 1].isspace():
        i -= 1
    end = i + 1
    while i >= 0 and data[i] in _IDENT_BYTES:
        i -= 1
    return True, data[i + 1 : end].decode("utf-8", "replace")


def extract(path_lang: str, text: str) -> FileFacts:
    """Parse one file and return its definitions, references and imports."""
    facts = FileFacts(lang=path_lang, n_lines=text.count("\n") + 1)
    parser = grammars.parser_for(path_lang)
    if parser is None:
        facts.error = f"no parser for {path_lang}"
        facts.reason = "no_parser"
        return facts
    # No capability means both query texts are empty, so the parse can only
    # return an empty match set. JSON alone is 96% of the files in one indexed
    # tree, at 14.85 s a pass.
    if not grammars.capabilities(path_lang):
        facts.reason = "no_capability"
        return facts

    data = text.encode("utf-8")
    tree = parser.parse(data)

    for _, caps in _run(facts, path_lang, queries.tags_source(path_lang), tree):
        names = caps.get("name") or []
        if not names:
            continue
        ident = names[0]
        for capture, nodes in caps.items():
            kind = queries.DEFINITION_KINDS.get(capture)
            if kind:
                whole = nodes[0]
                facts.definitions.append(
                    Definition(
                        kind=kind,
                        name=_text(data, ident),
                        start_byte=ident.start_byte,
                        end_byte=ident.end_byte,
                        start_line=whole.start_point[0] + 1,
                        end_line=whole.end_point[0] + 1,
                        body_end_byte=whole.end_byte,
                    )
                )
                continue
            edge = queries.REFERENCE_KINDS.get(capture)
            if edge:
                member, receiver = _member(data, ident)
                facts.references.append(
                    Reference(
                        kind=edge,
                        name=_text(data, ident),
                        call_site_byte=ident.start_byte,
                        line=ident.start_point[0] + 1,
                        is_member=member,
                        receiver=receiver,
                    )
                )

    _link(facts.definitions)
    for ref in facts.references:
        ref.scope = _enclosing(facts.definitions, ref.call_site_byte)

    facts.references = _dedup(facts.references, lambda r: (r.kind, r.name, r.call_site_byte))
    rows = _dedup(_imports(facts, path_lang, data, tree), lambda i: (i.module, i.symbol, i.alias))
    facts.imports = _narrow(rows)
    return facts


def _narrow(rows: list[Import]) -> list[Import]:
    """Drop a bare module row that a specific row from the same statement covers.

    A general import pattern matches every statement the specific ones match, so
    `import { Money } from "./money"` yields the module alone as well as the
    symbol. Two rows for one statement double-count the module edge.
    """
    named = {r.module for r in rows if r.symbol or r.alias}
    return [r for r in rows if r.symbol or r.alias or r.module not in named]


def _dedup(rows: list, key) -> list:
    """A concatenated query matches the same site twice, and it is one site.

    TypeScript runs JavaScript's patterns as well as its own, and a bare import
    pattern matches everything the specific ones match. Both produce a duplicate
    that would otherwise be counted as a second edge.
    """
    seen, out = set(), []
    for row in rows:
        k = key(row)
        if k in seen:
            continue
        seen.add(k)
        out.append(row)
    return out


def _imports(facts: FileFacts, lang: str, data: bytes, tree) -> list[Import]:
    """From the vendored query. No `tags.scm` supplies a usable import capture."""
    out: list[Import] = []
    for _, caps in _run(facts, lang, queries.import_source(lang), tree):
        mods = caps.get("module") or []
        syms = caps.get("symbol") or []
        aliases = caps.get("alias") or []
        if not mods and not syms:
            continue
        # Some grammars fold the surrounding space into the node, so the strip
        # runs before the quotes come off and again after.
        module = _text(data, mods[0]).strip().strip("\"'").strip() if mods else ""
        line = (mods or syms)[0].start_point[0] + 1
        if not syms:
            out.append(Import(module, alias=_text(data, aliases[0]) if aliases else "", line=line))
            continue
        # One record per symbol. `from a import x, y` is one match with two of
        # them, and taking only the first loses an import the scoping needs.
        paired = len(aliases) == len(syms)
        for i, sym in enumerate(syms):
            out.append(
                Import(
                    module,
                    symbol=_text(data, sym),
                    alias=_text(data, aliases[i]) if paired else "",
                    line=line,
                )
            )
    return out
