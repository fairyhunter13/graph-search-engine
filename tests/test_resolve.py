"""Ranked resolution, and the measurement the whole design rests on."""

from __future__ import annotations

import json
from pathlib import Path

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


RECEIVER = """\
from . import rates
from .rates import convert


def go(path):
    rates.convert(1)
    convert(2)
    return path.convert()
"""


def test_the_receiver_picks_the_module():
    """`T-93`. A member call names its module, and a stranger leaves the repo.

    Three call sites, one name. The receiver names the module, the receiver is
    absent, and the receiver is a local variable this file never imported. Only
    the third is external, and before `D-19` all three landed on `rates.convert`.
    """
    table = _table({"pkg/orders.py": RECEIVER, "pkg/rates.py": RATES, "other/rates.py": DECOY})
    facts = table.files["pkg/orders.py"]
    sites = [r for r in facts.references if r.name == "convert"]
    assert [r.receiver for r in sites] == ["rates", "", "path"]

    through_module, bare, stranger = (
        resolve.resolve_reference(table, "pkg/orders.py", r) for r in sites
    )
    assert through_module.resolved
    assert through_module.candidates[0].symbol.path == "pkg/rates.py"
    assert bare.resolved
    assert bare.candidates[0].symbol.path == "pkg/rates.py"
    assert stranger.external is True
    assert stranger.candidates == []


EXPRESSION_RECEIVER = """\
from .rates import convert


def go(raw):
    return Path(raw).convert()
"""


def test_an_expression_receiver_leaves_the_repo_rather_than_picking_a_homonym():
    """`T-208`. `Path(x).convert()` names no module, so it names no target.

    `extract._member` reports the call as a member with an empty receiver,
    because the byte before the dot closes a call. Reading that empty string as
    `the receiver decides nothing` scored the whole pool, and the two-engine
    measurement carried twenty false positives of exactly this shape.
    """
    table = _table(
        {"pkg/orders.py": EXPRESSION_RECEIVER, "pkg/rates.py": RATES, "other/rates.py": DECOY}
    )
    site = next(r for r in table.files["pkg/orders.py"].references if r.name == "convert")
    assert site.is_member is True
    assert site.receiver == ""

    got = resolve.resolve_reference(table, "pkg/orders.py", site)
    assert got.external is True
    assert got.candidates == []


def test_a_self_receiver_still_reaches_the_enclosing_class():
    """`self` names no module, so the class tier keeps pricing it."""
    table = _table({"pkg/orders.py": CALLER, "pkg/rates.py": RATES})
    got = _one(table, "pkg/orders.py", "subtotal")
    assert got.candidates[0].evidence == "same_class"


def test_a_constructor_resolves_through_the_class_and_never_through_init():
    """`T-199`: `__init__` matched 232 files in the CPython measurement.

    The rule held incidentally until this case: the call site captures the class
    name, so `__init__` is a definition and never a reference. A grammar bump that
    starts capturing the method name would collapse every constructor call onto
    one homonym, and only this direction of the assertion catches it.
    """
    sources = {
        f"pkg/m{i}.py": f"class C{i}:\n    def __init__(self):\n        self.x = {i}\n"
        for i in range(8)
    }
    sources["pkg/use.py"] = "from .m0 import C0\n\n\ndef make():\n    return C0()\n"
    table = _table(sources)

    got = _one(table, "pkg/use.py", "C0")
    assert got.resolved
    assert got.candidates[0].symbol.kind == "class"
    assert got.candidates[0].symbol.qualified_name == "C0"
    assert len(got.candidates) == 1

    # The other half. Eight files define `__init__`, and no call site names it.
    names = {r.name for facts in table.files.values() for r in facts.references}
    assert "__init__" not in names
    inits = [d for facts in table.files.values() for d in facts.definitions if d.name == "__init__"]
    assert len(inits) == 8


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


NODE_ID = "tests/test_resolve.py::test_import_scoping_collapses_candidates"


@pytest.mark.corpus
@pytest.mark.slow
def test_import_scoping_collapses_candidates():
    """The design premise, measured. If this stops holding, `D-03` goes blocked.

    The bands are wide on purpose. The claim is a collapse of roughly nine
    times, not a pair of exact numbers, and a corpus at a different tag moves
    both arms together. What is not allowed to move is the ratio.

    The scoped arm answers at fewer sites than the unscoped one, and that is the
    `D-19` rule and not a loss. A member call whose receiver names nothing this
    file imported leaves the repo, so it earns no edge at all. The refused share
    is asserted here because it is the price of the precision `T-91` measures.
    """
    if not (config.corpus_root() / "Lib").is_dir():
        pytest.skip(f"no corpus at {config.corpus_root()}")

    table = _corpus_table()
    assert len(table.files) > 500

    unscoped, unscoped_ambiguity, sites = resolve.mean_candidates(table, scoped=False)
    scoped, scoped_ambiguity, scoped_sites = resolve.mean_candidates(table, scoped=True)

    assert sites > 40000
    assert 8.0 <= unscoped <= 14.0
    assert 1.0 <= scoped <= 2.0
    assert unscoped / scoped >= 6.0
    assert unscoped_ambiguity > 0.45
    assert scoped_ambiguity < 0.25

    # `expr.method()` is about 43% of call sites, and the receiver rule refuses
    # them rather than guessing. A share far under this means the rule stopped
    # firing; far over it means it started eating calls it can resolve.
    assert 0.30 <= 1 - scoped_sites / sites <= 0.55

    _write_receipt(unscoped, scoped, len(table.files))


def _write_receipt(mean_global: float, mean_scoped: float, n_files: int) -> None:
    """The artifact the attester grades. A literal in test source grades nothing.

    This runs after the assertions, so the outcome it records is always a pass.
    """
    with config.receipt_lock(NODE_ID):
        config.write_receipt(
            NODE_ID,
            {
                "test_node_id": NODE_ID,
                "corpus_ref": config.CORPUS_REF,
                **config.provenance(Path(__file__).resolve().parent.parent),
                "outcome": "pass",
                "mean_global": round(mean_global, 4),
                "mean_scoped": round(mean_scoped, 4),
                "n_files": n_files,
            },
        )


CONCEPT = (
    Path(__file__).resolve().parent.parent
    / "knowledge"
    / "computations"
    / "import-scoping-collapses-the-candidate-set.md"
)


@pytest.mark.corpus
@pytest.mark.slow
def test_the_receipt_on_disk_agrees_with_the_concept():
    """The claim lives in the concept prose, and nothing compared the two.

    It sits in this file rather than beside the attester because pytest collects
    files in name order, so `test_attester.py` ran before the receipt existed and
    the check skipped on every CI run it was meant to guard.

    The claim is not parsed out of the prose. Each measured number is rendered
    the way the concept writes it and looked for there. So a number edited in the
    prose with no re-run fails, and a re-run that moves a number fails until the
    prose follows.
    """
    if not (config.corpus_root() / "Lib").is_dir():
        pytest.skip(f"no corpus at {config.corpus_root()}")

    receipt = json.loads(config.receipt_path(NODE_ID).read_text(encoding="utf-8"))
    assert receipt["corpus_ref"] == config.CORPUS_REF

    body = CONCEPT.read_text(encoding="utf-8")
    for field, rendered in (
        ("mean_global", f"{receipt['mean_global']:.2f}"),
        ("mean_scoped", f"{receipt['mean_scoped']:.2f}"),
        ("n_files", str(receipt["n_files"])),
    ):
        assert rendered in body, f"{field} measured {rendered}, and the concept does not say it"


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
