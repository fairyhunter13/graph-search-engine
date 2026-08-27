"""Tags queries, the capture normalizer, and the vendored import queries.

The pack ships 58 distinct capture names across its 68 `tags.scm` files, and the
vocabulary is the maintainer's rather than upstream's: it drifts with the pin.
So every name is either mapped to a kind here or listed as ignored, and a name
that is neither fails T-05 rather than being dropped at extraction time.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from tree_sitter_language_pack import get_tags_query

_QUERY_DIR = Path(__file__).resolve().parent / "queries"
IMPORT_QUERY_DIR = _QUERY_DIR / "imports"

# A repair layer for a measured gap in a pack query, concatenated after it. PHP
# ships no `scoped_call_expression` pattern, so `User::find()` -- the dominant
# call shape in a Laravel codebase -- captures nothing at all.
# The pin stays exact and the pack stays unforked. Each file names its gap.
TAGS_EXTRA_DIR = _QUERY_DIR / "tags_extra"

# A capture name inside a comment or a string literal is not a capture. Reading
# them raw yields `mailbox.org` from a `#match?` argument and a `local.scope`
# from a commented-out line, and both then read as vocabulary drift.
_COMMENT = re.compile(r";.*$", re.MULTILINE)
_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
_CAPTURE = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")

# ------------------------------------------------------------------ vocabulary

# A definition capture to the node kind it produces. The right-hand side is the
# closed set `store.NODE_KINDS` holds, so a new pack name maps into it or the
# schema grows in the same commit.
DEFINITION_KINDS: dict[str, str] = {
    "definition.class": "class",
    "definition.interface": "class",
    "definition.enum": "class",
    "definition.union": "class",
    "definition.type": "class",
    "definition.struct": "class",
    "definition.trait": "class",
    "definition.function": "function",
    "definition.macro": "function",
    "definition.operator": "function",
    "definition.constructor": "method",
    "definition.method": "method",
    "definition.field": "field",
    "definition.property": "field",
    "definition.slot": "field",
    "definition.event": "field",
    "definition.enum_variant": "constant",
    "definition.constant": "constant",
    "definition.variable": "constant",
    "definition.module": "module",
    "definition.namespace": "module",
    "definition.package": "module",
    # A hand-waved alias is still a definition site, and dropping it loses the
    # only name a re-export chain is reachable by.
    "definition.alias": "constant",
    # Three deviants. `intent` and `policy` are the `sas` private vocabulary and
    # `tag` is a markup grammar naming a document section.
    "definition.intent": "function",
    "definition.policy": "function",
    "definition.tag": "class",
    "definition.label": "constant",
    "definition.parameter": "field",
}

# A reference capture to the edge kind it produces. `reference.send` is csharp's
# spelling for a call and is the reason a call is not one capture name.
REFERENCE_KINDS: dict[str, str] = {
    "reference.call": "CALLS",
    "reference.send": "CALLS",
    "call": "CALLS",
    "reference.function": "CALLS",
    "reference.constructor": "CALLS",
    "reference.macro": "CALLS",
    "reference.implementation": "IMPLEMENTS",
    "reference.class": "REFERENCES",
    "reference.type": "REFERENCES",
    "reference.interface": "REFERENCES",
    "reference.module": "REFERENCES",
    "reference.constant": "REFERENCES",
    "reference.variable": "REFERENCES",
    "reference.field": "REFERENCES",
    "reference.property": "REFERENCES",
    "reference.enum_variant": "REFERENCES",
    "reference.union": "REFERENCES",
    "reference.alias": "REFERENCES",
    "reference.label": "REFERENCES",
    "reference.slot": "REFERENCES",
    "reference.unknown": "REFERENCES",
}

# Named, not defaulted. An underscore prefix is the pack's own "drop this", and
# the rest each have a reason that is not "we did not think about it".
IGNORED_CAPTURES: frozenset[str] = frozenset(
    {
        # The pack's own convention for a capture that exists to be matched on.
        "_annotation",
        "_name",
        "_test_attr",
        "reference._define",
        # `name` is the identifier every definition and reference hangs off, and
        # `doc` is the comment above it. Both are read directly, not dispatched.
        "name",
        "doc",
        "module",
        "call.name",
        # `sas` names its own import vocabulary and no import query reads it.
        "import",
        "import.source",
        # `cuda` leaks a locals capture into its tags file.
        "local.scope",
        # An explicit drop, and two grammars marking a test rather than a symbol.
        "ignore",
        "test.definition",
        "test.name",
    }
)

# TypeScript's tags file is a 23-line delta over JavaScript's. Run alone on a
# TypeScript tree it captures nothing at all, so the two concatenate. `tsx` is
# byte-identical to `typescript` and needs the same treatment.
QUERY_BASE: dict[str, str] = {"typescript": "javascript", "tsx": "javascript"}


def capture_names(source: str) -> frozenset[str]:
    """Every capture name in a query, with comments and string literals gone."""
    clean = _STRING.sub(" ", _COMMENT.sub("", source))
    return frozenset(_CAPTURE.findall(clean))


def unknown_captures(names: frozenset[str]) -> frozenset[str]:
    """Names that are neither mapped nor explicitly ignored. T-05 asserts empty."""
    known = set(DEFINITION_KINDS) | set(REFERENCE_KINDS) | IGNORED_CAPTURES
    return frozenset(names - known)


@cache
def pack_tags(lang: str) -> str:
    """The pack's own tags query, unrepaired. T-05 grades this, not the sum."""
    try:
        return get_tags_query(lang) or ""
    except Exception:
        return ""


@cache
def tags_extra(lang: str) -> str:
    path = TAGS_EXTRA_DIR / f"{lang}.scm"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


@cache
def tags_source(lang: str) -> str:
    """The query extraction runs: the base, the language's own, then the repair."""
    parts = [pack_tags(QUERY_BASE[lang])] if lang in QUERY_BASE else []
    parts += [pack_tags(lang), tags_extra(lang)]
    return "\n".join(p for p in parts if p)


@cache
def import_source(lang: str) -> str:
    """The vendored import query. `tags.scm` cannot supply one for any language.

    `QUERY_BASE` applies here too: TypeScript's import syntax is JavaScript's,
    and a second copy of the same patterns is a second thing to keep true.
    """
    path = IMPORT_QUERY_DIR / f"{lang}.scm"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    base = QUERY_BASE.get(lang)
    if base:
        return import_source(base)
    return ""


def languages_with_import_queries() -> frozenset[str]:
    if not IMPORT_QUERY_DIR.is_dir():
        return frozenset()
    return frozenset(p.stem for p in IMPORT_QUERY_DIR.glob("*.scm"))
