"""The capability table, measured under the pin rather than assumed."""

from __future__ import annotations

from graphrag import grammars, queries


def _tagged() -> list[str]:
    return sorted(lang for lang in grammars.known_languages() if queries.pack_tags(lang))


def _pack_only(lang: str) -> set[str]:
    """The pack's own capabilities, before concatenation and before repair."""
    found: set[str] = set()
    for name in queries.capture_names(queries.pack_tags(lang)):
        if queries.DEFINITION_KINDS.get(name):
            found.add("defs")
        edge = queries.REFERENCE_KINDS.get(name)
        if edge == "CALLS":
            found.add("calls")
        elif edge == "IMPLEMENTS":
            found.add("impls")
    return found


def test_capability_counts_under_the_pin():
    """Measured 2026-08-27 on tree-sitter-language-pack 1.15.8.

    Two tables, because they answer different questions. The pack census is what
    the wheel ships. The effective table is what this project answers with, and
    it is higher for `calls` because TypeScript and TSX concatenate JavaScript.
    """
    langs = grammars.known_languages()
    tagged = _tagged()
    assert len(langs) == 371
    assert len(tagged) == 68

    pack = {
        cap: sum(1 for lang in tagged if cap in _pack_only(lang))
        for cap in ("defs", "calls", "impls")
    }
    assert pack == {"defs": 67, "calls": 50, "impls": 17}

    effective = {
        cap: sum(1 for lang in tagged if cap in grammars.capabilities(lang))
        for cap in ("defs", "calls", "impls")
    }
    assert effective == {"defs": 67, "calls": 52, "impls": 17}

    # The one tagged grammar with no definition capture at all. A markup query
    # that names sections, so nothing it captures is a symbol.
    assert [lang for lang in tagged if "defs" not in grammars.capabilities(lang)] == ["svelte"]


def test_typescript_gains_calls_and_c_never_does():
    assert "calls" in grammars.capabilities("typescript")
    assert "calls" not in _pack_only("typescript")
    assert "calls" in grammars.capabilities("tsx")
    assert "calls" not in grammars.capabilities("c")


def test_a_missing_capability_is_a_sentence_and_a_present_one_is_empty():
    assert grammars.missing("python", "calls") == ""
    reason = grammars.missing("c", "calls")
    assert reason.startswith("c in this project")
    assert "no call capture" in reason


def test_a_language_with_no_grammar_has_no_capability():
    assert grammars.capabilities("not-a-language") == frozenset()
    assert grammars.parser_for("not-a-language") is None
    assert grammars.missing("not-a-language", "defs") != ""


def test_the_capability_table_covers_what_it_is_asked_for():
    table = grammars.capability_table(["python", "c", "python"])
    assert sorted(table) == ["c", "python"]
    assert table["python"] >= {"defs", "calls", "classes", "imports"}
    for caps in table.values():
        assert caps <= grammars.CAPABILITIES


# A name the pack resolves to another grammar's parser and then caches under the
# alias. The manifest does not list either, so a cached name outside the manifest
# is an alias and never a grammar the table missed.
PACK_ALIASES = frozenset({"lisp", "shell"})


def test_known_languages_does_not_depend_on_the_download_cache():
    """The manifest is the table, and the cache is a subset of it plus the aliases.

    The cache is download history and it grows as a machine parses more, so the
    assertion is a containment and never an equality. The capability table reads
    the manifest, which is why it never shrinks to what this machine happens to
    have fetched.
    """
    known = grammars.known_languages()
    assert grammars.cached_languages() - known <= PACK_ALIASES
    assert len(known) > len(grammars.cached_languages())
