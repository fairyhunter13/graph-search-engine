"""SCIP symbol strings, read for the one thing this engine needs: a name.

A symbol is `<scheme> <manager> <package> <version> <descriptors>`, and the
descriptor suffix carries the kind. Names may be backtick-quoted, where a
doubled backtick is a literal one, so a split on space or on `.` is wrong for
any identifier holding either.

Nothing here resolves a symbol. The name is what joins a SCIP occurrence to a
node this engine already extracted, and the byte range does the rest.
"""

from __future__ import annotations

from dataclasses import dataclass

LOCAL = "local"

# `SymbolInformation.Kind`, from `scip.proto` v0.9.0, folded onto this engine's
# eight node kinds. Only the values a graph query distinguishes are here: a kind
# with no entry keeps whatever tree-sitter found, which is the same rule as 0.
_KIND: dict[int, str] = {
    7: "class",
    21: "class",
    49: "class",
    53: "class",
    11: "class",
    17: "function",
    25: "function",
    26: "method",
    80: "method",
    9: "method",
    41: "method",
    15: "field",
    61: "field",
    12: "field",
    8: "constant",
    29: "module",
    30: "module",
    35: "module",
}


def kind_of(value: int) -> str:
    """A SCIP kind as a node kind, or an empty string where it says nothing.

    Five of the ten live indexers leave the field at 0, so an empty answer is
    the common case and never an error.
    """
    return _KIND.get(value, "")


# The descriptor suffixes, and the node kind each one implies. `scip-python`
# and four others leave `SymbolInformation.kind` at 0, so the suffix is the
# only kind signal those indexes carry.
_SUFFIX_KIND = {
    "/": "module",
    "#": "class",
    ".": "function",
    ":": "field",
    "!": "function",
}


@dataclass(frozen=True, slots=True)
class Descriptor:
    name: str
    kind: str


def _unquote(raw: str) -> str:
    if not raw.startswith("`"):
        return raw
    return raw[1:-1].replace("``", "`") if raw.endswith("`") else raw[1:]


def _split_descriptors(text: str) -> list[str]:
    """Cut on a suffix, respecting a backtick-quoted name and a `(...)` group."""
    out: list[str] = []
    start = depth = 0
    i = 0
    while i < len(text):
        char = text[i]
        if char == "`":
            i += 1
            while i < len(text):
                if text[i] == "`":
                    if i + 1 < len(text) and text[i + 1] == "`":
                        i += 2
                        continue
                    break
                i += 1
        elif char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
            if depth == 0 and (i + 1 >= len(text) or text[i + 1] not in "."):
                out.append(text[start : i + 1])
                start = i + 1
        elif depth == 0 and char in _SUFFIX_KIND:
            out.append(text[start : i + 1])
            start = i + 1
        i += 1
    if start < len(text):
        out.append(text[start:])
    return [d for d in out if d]


def descriptors(symbol: str) -> list[Descriptor]:
    """Every descriptor in a symbol, outermost first. A local has none."""
    if not symbol or symbol.startswith(LOCAL + " "):
        return []
    parts = symbol.split(" ", 4)
    if len(parts) < 5:
        return []
    out: list[Descriptor] = []
    for raw in _split_descriptors(parts[4]):
        if raw.startswith(("(", "[")):
            out.append(Descriptor(_unquote(raw[1:-1]), "field"))
            continue
        suffix = raw[-1]
        body = raw[:-1]
        kind = _SUFFIX_KIND.get(suffix, "function")
        if body.endswith(")"):
            body = body[: body.rindex("(")]
            kind = "method"
        out.append(Descriptor(_unquote(body), kind))
    return out


def name(symbol: str) -> str:
    """The last descriptor, which is what the symbol is called."""
    got = descriptors(symbol)
    return got[-1].name if got else ""


def is_local(symbol: str) -> bool:
    """A local never leaves its document, so it joins nothing across files."""
    return symbol.startswith(LOCAL + " ")
