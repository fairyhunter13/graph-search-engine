"""The capture vocabulary, and the concatenation the pack's TypeScript query needs."""

from __future__ import annotations

from graphrag import extract, grammars, queries

FIXTURE = "class A { run() { this.go(); } }\n"


def _tagged() -> list[str]:
    return sorted(lang for lang in grammars.known_languages() if queries.pack_tags(lang))


def test_every_capture_name_is_known():
    """A pin bump that adds a name fails here rather than dropping the data."""
    names: set[str] = set()
    for lang in _tagged():
        names |= queries.capture_names(queries.pack_tags(lang))
    assert queries.unknown_captures(frozenset(names)) == frozenset()
    assert len(names) == 58


def test_a_capture_name_in_a_comment_is_not_a_capture():
    source = '; @reference.call is documentation\n(x) @definition.class\n"@local.scope"\n'
    assert queries.capture_names(source) == frozenset({"definition.class"})


def test_an_unmapped_name_is_reported_rather_than_dropped():
    assert queries.unknown_captures(frozenset({"definition.class", "reference.wombat"})) == (
        frozenset({"reference.wombat"})
    )


def test_typescript_concatenates_javascript():
    """TypeScript's tags file is a delta, and alone it captures nothing at all."""
    facts = extract.FileFacts(lang="typescript")
    alone = extract._run(facts, "typescript", queries.pack_tags("typescript"), _tree())
    assert alone == []

    facts = extract.extract("typescript", FIXTURE)
    assert {r.kind for r in facts.references} == {"CALLS"}
    assert queries.pack_tags("javascript") in queries.tags_source("typescript")
    assert queries.tags_source("tsx") == queries.tags_source("typescript")


def _tree():
    parser = grammars.parser_for("typescript")
    assert parser is not None
    return parser.parse(FIXTURE.encode("utf-8"))


def test_the_repair_layer_is_appended_and_the_pack_query_is_untouched():
    assert queries.tags_extra("php")
    assert queries.tags_extra("php") not in queries.pack_tags("php")
    assert queries.tags_source("php").endswith(queries.tags_extra("php"))
    assert queries.tags_extra("python") == ""


def test_an_import_query_follows_the_base_language():
    assert queries.import_source("typescript") == queries.import_source("javascript")
    assert queries.import_source("not-a-language") == ""
    assert queries.languages_with_import_queries() >= {"python", "javascript", "php"}
