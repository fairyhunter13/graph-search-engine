"""Every vendored import query, compiled and run on a real snippet.

A pattern naming a node the grammar does not carry makes the whole query fail to
compile, and the extractor returns no imports rather than raising. So the file
reads as a language with no import syntax, which is the silent gap this engine
exists to avoid. The compile case is what catches it.
"""

from __future__ import annotations

import pytest
from tree_sitter import Query

from graphrag import extract, grammars, queries

# One snippet per language, and the module the query must find in it. Real
# source in every case, because a parser stub proves nothing about a grammar.
SAMPLES: dict[str, tuple[str, str]] = {
    "c": ('#include <stdio.h>\n#include "local.h"\n', "<stdio.h>"),
    "cpp": ('#include <vector>\n#include "local.hpp"\n', "<vector>"),
    "csharp": ("using System;\nusing S = System.Text;\n", "System"),
    "cython": ("import os\nfrom a cimport b\n", "os"),
    "d": ("import std.stdio;\nimport std.conv : to;\n", "std.stdio"),
    "dart": ("import 'dart:math';\nimport 'p.dart' as p;\n", "dart:math"),
    "elixir": ("defmodule M do\n  import Enum\nend\n", "Enum"),
    "elm": ("module M exposing (..)\nimport Html exposing (div)\n", "Html"),
    "fortran": ("program p\n  use iso_fortran_env\nend program p\n", "iso_fortran_env"),
    "gdshader": ('#include "a.gdshaderinc"\n', "a.gdshaderinc"),
    "gleam": ("import gleam/io\n", "gleam/io"),
    "go": ('package m\nimport "fmt"\n', "fmt"),
    "java": ("package a.b;\nimport java.util.List;\n", "java.util.List"),
    "javascript": ("import fs from 'fs';\n", "fs"),
    "kotlin": ("package a.b\nimport kotlin.math.max\n", "kotlin.math.max"),
    "lua": ('local m = require("mod")\n', "mod"),
    "mojo": ("from a import b\nimport os\n", "a"),
    "ocaml": ("open Core\n", "Core"),
    "php": ("<?php\nuse App\\Models\\User;\n", "App\\Models\\User"),
    "pony": ('use "collections"\n', "collections"),
    "python": ("import os\nfrom a.b import thing\n", "os"),
    "ql": ("import javascript\n", "javascript"),
    "r": ("library(dplyr)\n", "dplyr"),
    "ruby": ('require "json"\n', "json"),
    "rust": ("use std::collections::HashMap;\n", "std::collections::HashMap"),
    "snakemake": ('include: "rules/a.smk"\n', "rules/a.smk"),
    "solidity": ('import "./A.sol";\n', "./A.sol"),
    "sourcepawn": ("#include <sourcemod>\n", "<sourcemod>"),
    "stan": ("functions {\n#include helper.stan\n}\n", "helper.stan"),
    "swift": ("import Foundation\n", "Foundation"),
    "tact": ('import "./a";\n', "./a"),
    "templ": ('package m\nimport "fmt"\n', "fmt"),
    "typescript": ("import { Money } from './money';\n", "./money"),
}


def _vendored() -> list[str]:
    return sorted(queries.languages_with_import_queries())


def test_every_vendored_import_query_compiles():
    """A bad node type kills the whole query, and the extractor swallows it."""
    broken = {}
    for lang in _vendored():
        parser = grammars.parser_for(lang)
        if parser is None:
            continue
        try:
            Query(parser.language, queries.import_source(lang))
        except Exception as exc:
            broken[lang] = str(exc)
    assert broken == {}


@pytest.mark.parametrize("lang", sorted(SAMPLES))
def test_each_language_extracts_an_import(lang):
    """`T-11`: the query finds the module a reader would name in the snippet."""
    code, want = SAMPLES[lang]
    if grammars.parser_for(lang) is None:
        pytest.skip(f"no parser cached for {lang}")

    facts = extract.extract(lang, code)
    assert facts.error == ""
    assert want in [row.module for row in facts.imports]


def test_every_vendored_query_has_a_sample():
    """A query nothing runs is a query nobody knows is broken."""
    covered = set(SAMPLES) | {"tsx"}
    assert set(_vendored()) - covered == set()


def test_a_language_with_no_import_query_says_so():
    """Scala spells a dotted path as sibling nodes, so it has no query yet."""
    assert queries.import_source("scala") == ""
    assert "imports" not in grammars.capabilities("scala")
    assert grammars.missing("scala", "imports").startswith("scala in this project")
