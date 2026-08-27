"""Ranked resolution, and the measurement the whole design rests on."""

from __future__ import annotations

import pytest

from graphrag import config, extract, resolve, symtab

CALLER = """\
from .rates import convert


class Order:
    def subtotal(self):
        return 1

    def tax(self):
        return convert(self.subtotal())


def loose():
    return convert(0)
"""

RATES = """\
def convert(x):
    return x


def subtotal():
    return 0
"""

DECOY = """\
def convert(x):
    return x
"""


def _table(sources: dict[str, str]) -> symtab.SymbolTable:
    return symtab.build({p: extract.extract("python", t) for p, t in sources.items()})


def _one(table, path, name) -> resolve.Resolution:
    facts = table.files[path]
    ref = next(r for r in facts.references if r.name == name)
    return resolve.resolve_reference(table, path, ref)


def test_a_same_class_call_beats_every_other_candidate():
    table = _table({"pkg/orders.py": CALLER, "pkg/rates.py": RATES})
    got = _one(table, "pkg/orders.py", "subtotal")
    assert got.resolved
    assert got.candidates[0].evidence == "same_class"
    assert got.candidates[0].confidence == resolve.SAME_CLASS
    assert got.candidates[0].symbol.qualified_name == "Order.subtotal"


def test_an_imported_symbol_beats_a_repo_wide_homonym():
    table = _table({"pkg/orders.py": CALLER, "pkg/rates.py": RATES, "other/rates.py": DECOY})
    got = _one(table, "pkg/orders.py", "convert")
    assert got.resolved
    assert got.candidates[0].evidence == "import"
    assert got.candidates[0].symbol.path == "pkg/rates.py"


def test_unknown_name_is_external():
    """A name defined nowhere is never forced onto an in-repo homonym."""
    table = _table({"pkg/orders.py": "def go():\n    return absent()\n"})
    got = _one(table, "pkg/orders.py", "absent")
    assert got.external is True
    assert got.candidates == []
    assert got.resolved is False


def test_an_out_of_scope_name_falls_to_a_ranked_global_set():
    sources = {f"m{i}/x.py": DECOY for i in range(4)}
    sources["far/caller.py"] = "def go():\n    return convert(1)\n"
    got = _one(_table(sources), "far/caller.py", "convert")
    assert got.candidate_count == 4
    assert got.resolved is False
    assert {c.evidence for c in got.candidates} == {"global"}
    assert got.candidates[0].confidence == pytest.approx(resolve.GLOBAL_UNIQUE / 4)


def test_a_global_set_below_the_floor_is_dropped_rather_than_ranked():
    n = int(resolve.GLOBAL_UNIQUE / config.CONFIDENCE_FLOOR) + 2
    sources = {f"m{i}/x.py": DECOY for i in range(n)}
    sources["far/caller.py"] = "def go():\n    return convert(1)\n"
    got = _one(_table(sources), "far/caller.py", "convert")
    assert got.candidates == []
    assert got.external is False


def test_a_relative_import_resolves_against_the_importing_directory():
    assert symtab.resolve_module("pkg/orders.py", ".rates") == "pkg.rates"
    assert symtab.resolve_module("pkg/__init__.py", ".rates") == "pkg.rates"
    assert symtab.resolve_module("a/b/mod.py", "..top") == "a.top"
    assert symtab.resolve_module("pkg/orders.py", "decimal") == "decimal"


def test_a_package_initialiser_names_the_package():
    assert symtab.module_name("pkg/__init__.py") == "pkg"
    assert symtab.module_name("pkg/rates.py") == "pkg.rates"


def test_a_source_root_prefix_leaves_the_module_name():
    """`T-59`: a build-tool directory is no part of the name an import writes."""
    assert symtab.module_name("src/main/java/com/acme/Rates.java") == "com.acme.Rates"
    assert symtab.module_name("app/src/main/kotlin/com/acme/Rates.kt") == "com.acme.Rates"
    assert symtab.module_name("src/graphrag/symtab.py") == "graphrag.symtab"
    # The longest prefix wins, so `src` never eats the java layout halfway.
    assert symtab.module_name("src/test/scala/com/acme/RatesSpec.scala") == "com.acme.RatesSpec"
    # A file directly under a source root keeps its own name, because an empty
    # module would make every such file the same module.
    assert symtab.module_name("src/rates.py") == "rates"
    assert symtab.module_name("src.py") == "src"
    # A relative import agrees with the module name, or scoping compares a
    # stripped path against an unstripped one and matches nothing.
    assert symtab.resolve_module("src/pkg/orders.py", ".rates") == "pkg.rates"


def _corpus_table():
    root = config.corpus_root() / "Lib"
    files = {}
    for path in sorted(root.rglob("*.py")):
        if "test" in path.parts or "site-packages" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        files[str(path.relative_to(root))] = extract.extract("python", text)
    return symtab.build(files)


@pytest.mark.corpus
@pytest.mark.slow
def test_import_scoping_collapses_candidates():
    """The design premise, measured. If this stops holding, `D-03` goes blocked.

    The bands are wide on purpose. The claim is a collapse of roughly seven
    times, not a pair of exact numbers, and a corpus at a different tag moves
    both arms together. What is not allowed to move is the ratio.
    """
    if not (config.corpus_root() / "Lib").is_dir():
        pytest.skip(f"no corpus at {config.corpus_root()}")

    table = _corpus_table()
    assert len(table.files) > 500

    unscoped, unscoped_ambiguity, sites = resolve.mean_candidates(table, scoped=False)
    scoped, scoped_ambiguity, scoped_sites = resolve.mean_candidates(table, scoped=True)

    assert sites > 40000
    assert scoped_sites > 40000
    assert 8.0 <= unscoped <= 14.0
    assert 1.0 <= scoped <= 2.0
    assert unscoped / scoped >= 6.0
    assert unscoped_ambiguity > 0.45
    assert scoped_ambiguity < 0.25


@pytest.mark.corpus
@pytest.mark.slow
def test_the_definition_unit_is_higher_than_the_file_unit():
    """One file defining a name twice is two edges and one place to look."""
    if not (config.corpus_root() / "Lib").is_dir():
        pytest.skip(f"no corpus at {config.corpus_root()}")

    table = _corpus_table()
    by_file, _, _ = resolve.mean_candidates(table, scoped=False, unit="file")
    by_def, _, _ = resolve.mean_candidates(table, scoped=False, unit="definition")
    assert by_def > by_file

    with pytest.raises(ValueError):
        resolve.mean_candidates(table, scoped=False, unit="module")
