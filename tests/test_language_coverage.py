"""A caller question, answered in every language whose grammar can express one.

`test_import_queries.py`'s `SAMPLES` dict is the established shape for a one-snippet-per-language
case here, and this file follows it rather than inventing a fixture-directory convention.
"""

from __future__ import annotations

import pytest

from graphrag import extract, grammars

# One snippet per language this project added a call capture for on 2026-09-27:
# a function that calls another, and the callee's own name. `vue` and `svelte`
# route through TypeScript, so their snippet is a single-file component.
CALL_SAMPLES: dict[str, tuple[str, str]] = {
    "bash": ("baz() {\n  echo 1\n}\nbar() {\n  baz\n}\n", "baz"),
    "c": ("int baz(void) { return 1; }\nint bar(void) { return baz(); }\n", "baz"),
    "cuda": (
        "__device__ int baz() { return 1; }\n__global__ void bar() { baz(); }\n",
        "baz",
    ),
    "fsharp": ("let baz () = 1\nlet bar () = baz ()\n", "baz"),
    "haskell": ("baz :: Int\nbaz = 1\n\nbar :: Int\nbar = baz 1\n", "baz"),
    "hcl": ('variable "x" {\n  default = join(",", [1, 2])\n}\n', "join"),
    "perl": ("sub baz { return 1; }\nsub bar { return baz(); }\n", "baz"),
    "sql": (
        "CREATE FUNCTION baz() RETURNS int AS $$ SELECT 1 $$ LANGUAGE sql;\n"
        "CREATE FUNCTION bar() RETURNS int AS $$ SELECT baz() $$ LANGUAGE sql;\n",
        "baz",
    ),
    "swift": ("func baz() -> Int { return 1 }\nfunc bar() -> Int { return baz() }\n", "baz"),
    "terraform": ('variable "x" {\n  default = join(",", [1, 2])\n}\n', "join"),
    "zig": ("fn baz() i32 { return 1; }\nfn bar() i32 { return baz(); }\n", "baz"),
    "vue": (
        '<script lang="ts">\nfunction baz(): number {\n  return 1\n}\n'
        "function bar(): number {\n  return baz()\n}\n</script>\n",
        "baz",
    ),
    "svelte": (
        "<script>\nfunction baz() {\n  return 1\n}\nfunction bar() {\n  return baz()\n}\n</script>\n",
        "baz",
    ),
}

# `julia` and `elisp` gained no call capture: each grammar makes a real call
# indistinguishable from something else syntactically identical -- a
# function's own zero-argument signature for Julia, a quoted list literal for
# Elisp -- and a wrong edge is worse than an absent one. `defs` still measures.
DEFS_ONLY: frozenset[str] = frozenset({"julia", "elisp"})


@pytest.mark.parametrize("lang", sorted(CALL_SAMPLES))
def test_every_new_language_reports_a_call_edge(lang):
    """`T-362`. A caller question is answerable, not only a capability flag."""
    code, callee = CALL_SAMPLES[lang]
    assert "calls" in grammars.capabilities(lang)

    facts = extract.extract(lang, code)
    assert facts.error == ""
    assert callee in {r.name for r in facts.references if r.kind == "CALLS"}


@pytest.mark.parametrize("lang", sorted(DEFS_ONLY))
def test_a_grammar_that_cannot_tell_a_call_from_its_lookalike_stays_defs_only(lang):
    """`T-363`. `calls` absent is the honest answer, not a missing repair file."""
    assert "defs" in grammars.capabilities(lang)
    assert "calls" not in grammars.capabilities(lang)


def test_julia_never_records_a_function_calling_its_own_signature():
    """`T-364`. The defect this project chose not to ship: every function
    reading as its own caller, because `function baz()` and `baz()` share one
    node shape and the base query engine has no ancestor-exclusion predicate.
    """
    facts = extract.extract(
        "julia", "function baz()\n    return 1\nend\n\nfunction bar()\n    return baz()\nend\n"
    )
    assert [d.name for d in facts.definitions] == ["baz", "bar"]
    assert facts.references == []


def test_a_quoted_elisp_list_never_becomes_a_definitions_own_caller():
    """`T-365`. `(baz)` reads as a real call syntactically and `'(baz)` does
    not, and this project has no way to write only the first as a capture, so
    it writes neither -- `elisp` keeps the defs its pack query already had.
    """
    facts = extract.extract("elisp", "(defun baz () 1)\n(defun bar () (baz) '(baz qux))\n")
    assert {d.name for d in facts.definitions} == {"baz", "bar"}
    assert facts.references == []


def test_vue_and_svelte_place_a_definition_on_the_outer_files_own_line():
    """`T-366`. The `<script>` tag itself, and any markup above it, shift
    every definition and reference by the same number of lines.
    """
    src = (
        "<template>\n  <div />\n</template>\n"
        '<script lang="ts">\n'
        "function baz(): number {\n  return 1\n}\n"
        "function bar(): number {\n  return baz()\n}\n"
        "</script>\n"
    )
    facts = extract.extract("vue", src)
    lines = {d.name: d.start_line for d in facts.definitions}
    assert lines == {"baz": 5, "bar": 8}
    assert [r.line for r in facts.references if r.kind == "CALLS"] == [9]


def test_a_component_with_no_script_block_answers_no_symbols_not_an_error():
    """`T-367`. Template-only markup is a real, common `.vue`/`.svelte` file
    shape, and it must read as `no_symbols`, never as a parse failure.
    """
    facts = extract.extract("vue", "<template>\n  <div />\n</template>\n")
    assert facts.error == ""
    assert facts.reason == "no_symbols"
    assert facts.definitions == []
