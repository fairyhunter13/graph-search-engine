"""Pack access, and the capability set per language.

A capability is per capture, never per language. 68 of the pack's 371 grammars
ship a `tags.scm`, and 18 of those 68 emit no call capture at all: C, Swift,
TypeScript and TSX among them. So "has a tags file" and "answers who calls this"
are different questions, and a tier would conflate them.

Two of the 18 recover. TypeScript and TSX gain calls from the JavaScript query
they concatenate, so the table this module reports holds 52 and the pack census
holds 50. `T-06` asserts both, because they answer different questions.

Capability is read from the query text, which the wheel carries. No parser is
downloaded to answer it, so `doctor` reports the table offline.
"""

from __future__ import annotations

from functools import cache

from tree_sitter_language_pack import (
    available_languages,
    get_parser,
    manifest_languages,
)

from . import queries

# The six capabilities a query answer reports. A name outside this set is a bug
# rather than a language that has it.
CAPABILITIES: frozenset[str] = frozenset(
    {"defs", "calls", "classes", "methods", "imports", "impls"}
)

# What a missing capability means, in the words the answer uses. An empty list
# is the failure this project exists to avoid, so every gap has a sentence.
GAP_REASON: dict[str, str] = {
    "defs": "has no definition capture, so no symbol is extracted",
    "calls": "has no call capture, so no caller question is answerable",
    "classes": "has no class capture, so no type is extracted",
    "methods": "has no method capture, and a method reads as a function",
    "imports": "has no import query, so resolution falls back to repo-global",
    "impls": "has no implementation capture, so no interface edge is extracted",
}


def known_languages() -> frozenset[str]:
    """Every grammar the pin ships, cached or not.

    `available_languages()` reports only what is already downloaded, so using it
    for capability detection makes the table depend on download history.
    """
    return frozenset(manifest_languages())


def cached_languages() -> frozenset[str]:
    return frozenset(available_languages())


@cache
def capabilities(lang: str) -> frozenset[str]:
    """The capability set, read out of the query text."""
    if lang not in known_languages():
        return frozenset()

    names = queries.capture_names(queries.tags_source(lang))
    found = set()
    for name in names:
        kind = queries.DEFINITION_KINDS.get(name)
        if kind:
            found.add("defs")
            if kind == "class":
                found.add("classes")
            elif kind == "method":
                found.add("methods")
        edge = queries.REFERENCE_KINDS.get(name)
        if edge == "CALLS":
            found.add("calls")
        elif edge == "IMPLEMENTS":
            found.add("impls")
    if queries.import_source(lang):
        found.add("imports")
    return frozenset(found)


def missing(lang: str, wanted: str) -> str:
    """The sentence an answer prints where a capability is absent, else empty."""
    if wanted in capabilities(lang):
        return ""
    reason = GAP_REASON.get(wanted, f"has no {wanted} capability")
    return f"{lang} in this project {reason}"


def capability_table(langs: object) -> dict[str, frozenset[str]]:
    """What `doctor` prints, and what every query answer carries."""
    return {lang: capabilities(lang) for lang in sorted(set(langs))}  # type: ignore[call-overload]


@cache
def parser_for(lang: str):
    """The parser, downloading it on first use.

    The pack fetches a per-language shared object into `~/.cache` the first time
    it is asked. First run needs network, and an air-gapped install seeds that
    cache. A failure here is returned as None, so a project indexes its other
    languages rather than failing whole.
    """
    try:
        return get_parser(lang)
    except Exception:
        return None
