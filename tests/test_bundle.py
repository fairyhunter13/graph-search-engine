"""The knowledge bundle, checked from the repo rather than from the checker.

`okfrules` runs in the gate and grades the bundle against its own rules. These
cases hold what the gate cannot see: that the root declares a version this repo
actually targets, that the timestamp trap upstream documents is not reachable
through this repo's own reader, and that the trust tier reads both shapes of a
verification stamp.

The reader under test is the one the gate runs. It used to live here, and the
shipped check called `yaml.safe_load` instead, so the fix and the trap were in
different files.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "knowledge"

sys.path.insert(0, str(ROOT / "scripts"))

import check_index_gloss  # noqa: E402
import check_no_shrink  # noqa: E402
import okf_frontmatter  # noqa: E402
from okf_frontmatter import FrontmatterLoader, frontmatter  # noqa: E402


def _concepts() -> list[Path]:
    return [p for p in sorted(BUNDLE.rglob("*.md")) if p.name not in ("index.md", "log.md")]


def test_root_index_declares_okf_version():
    front = frontmatter(BUNDLE / "index.md")
    assert front["okf_version"] == "0.2"

    others = [p for p in BUNDLE.rglob("index.md") if p != BUNDLE / "index.md"]
    assert others, "the bundle has no directory index"
    for path in others:
        assert frontmatter(path) == {}, f"{path} carries frontmatter and only the root may"


def test_every_concept_carries_the_families_this_repo_writes():
    concepts = _concepts()
    assert concepts
    for path in concepts:
        front = frontmatter(path)
        assert front.get("type"), path
        assert front.get("title"), path
        assert front.get("description"), path
        assert front.get("generated", {}).get("by"), path


def test_a_timestamp_survives_a_round_trip_through_this_reader():
    """The PyYAML trap, proven on a value the bundle would actually carry."""
    raw = "stale_after: 2027-08-27T00:00:00Z\n"
    loaded = yaml.load(raw, Loader=FrontmatterLoader)
    assert loaded["stale_after"] == "2027-08-27T00:00:00Z"
    assert yaml.safe_dump(loaded).strip() == "stale_after: '2027-08-27T00:00:00Z'"

    # The stock loader is the trap, so what it does is asserted rather than
    # described. It hands back a datetime, and a datetime dumps back offset-free.
    assert not isinstance(yaml.safe_load(raw)["stale_after"], str)


_LINK = re.compile(r"\]\(([^)\s]+)\)")


def test_no_link_in_the_bundle_starts_at_the_root():
    """The spec recommends a leading slash and GitHub renders it as a 404."""
    for path in sorted(BUNDLE.rglob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            assert "](/" not in line, f"{path}: {line}"


def test_every_relative_link_in_the_bundle_resolves():
    """The other half. A link with no slash is well formed and still dead.

    Checked from the file's own directory, because that is what a relative link
    means and what GitHub does with it.
    """
    for path in sorted(BUNDLE.rglob("*.md")):
        for target in _LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            landing = (path.parent / target.split("#")[0]).resolve()
            assert landing.exists(), f"{path}: {target}"


def _okfrules(args: list[str], target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["okfrules", *args, "check", str(target)], capture_output=True, text=True)


CONCEPT = """\
---
type: Constraint
title: An offset-free date reads as fresh forever
description: The fixture the strict arm is proven against.
sources:
  - id: spec
    resource: https://example.invalid/spec
stale_after: 2026-09-23
---

# Body

Text.
"""

INDEX = """\
---
okf_version: "0.2"
---

# Constraint

* [An offset-free date reads as fresh forever](c.md) - The fixture the strict arm is proven
  against.
"""


@pytest.mark.skipif(shutil.which("okfrules") is None, reason="okfrules is not on PATH")
def test_offset_free_stale_after_is_rejected(tmp_path):
    """Both ways, because the second half is what makes `-strict` the line that matters."""
    (tmp_path / "index.md").write_text(INDEX)
    (tmp_path / "c.md").write_text(CONCEPT)

    strict = _okfrules(["-strict"], tmp_path)
    assert strict.returncode != 0
    assert "explicit UTC offset" in strict.stdout + strict.stderr

    plain = _okfrules([], tmp_path)
    assert plain.returncode == 0, plain.stdout + plain.stderr


def test_dropped_receipt_field_fails(tmp_path):
    """A receipt field the attester never reads is a claim nothing checks.

    The break lands on a copy. An earlier version edited the tracked concept and
    restored it in a `finally`, which leaves the working tree dirty the moment
    the run is killed between the two writes.
    """
    contract = ROOT / "scripts" / "check_attester_contract.py"
    spec = importlib.util.spec_from_file_location("check_attester_contract", contract)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.check(BUNDLE) == []

    bundle = tmp_path / "knowledge"
    shutil.copytree(BUNDLE, bundle)
    concept = bundle / "computations" / "import-scoping-collapses-the-candidate-set.md"
    text = concept.read_text(encoding="utf-8")
    broken = text.replace("commit_sha,", "commit_sha, wall_clock_s,")
    assert broken != text
    concept.write_text(broken, encoding="utf-8")
    findings = module.check(bundle)
    assert len(findings) == 1
    assert "wall_clock_s" in findings[0]


def test_the_trust_tier_reads_the_three_cases_section_5_3_names():
    """No key, a machine actor, and a person, lowest to highest."""
    assert okf_frontmatter.trust_tier({}) == "unverified"
    assert okf_frontmatter.trust_tier({"verified": []}) == "unverified"

    machine = {"verified": [{"by": "process:okf-verify", "at": "2026-08-27T11:36:40Z"}]}
    assert okf_frontmatter.trust_tier(machine) == "machine-confirmed"

    # Never written by this repo. The fleet hook refuses one, so the tier it
    # produces is graded on a literal here and against no concept on disk.
    reviewed = {"verified": [{"by": "human:maintainer", "at": "2026-08-27T11:36:40Z"}]}
    assert okf_frontmatter.trust_tier(reviewed) == "human-reviewed"

    both = {"verified": [machine["verified"][0], reviewed["verified"][0]]}
    assert okf_frontmatter.trust_tier(both) == "human-reviewed"


def test_a_bare_verified_mapping_reads_as_a_one_element_list():
    """Section 11 makes this a MUST, and it is one line of code to get wrong."""
    stamp = "{ by: process:okf-verify, at: 2026-08-27T11:36:40Z }"
    bare = okf_frontmatter.loads(f"verified: {stamp}\n")
    listed = okf_frontmatter.loads(f"verified:\n  - {stamp}\n")

    assert okf_frontmatter.verifiers(bare) == okf_frontmatter.verifiers(listed)
    assert okf_frontmatter.trust_tier(bare) == okf_frontmatter.trust_tier(listed)
    assert okf_frontmatter.trust_tier(bare) == "machine-confirmed"


def test_a_concept_reads_as_reviewed_only_where_a_human_stamped_it():
    """The tier over the concepts on disk, so the reader runs on real files.

    This held `human-reviewed` out of the bundle until `maintainer` stamped the
    import-scoping computation. That was the state and never the rule, and the
    rule is that the tier follows a `human:` actor rather than any other.
    """
    tiers, stamped = [], []
    for path in _concepts():
        front = frontmatter(path)
        tiers.append(okf_frontmatter.trust_tier(front))
        stamped.append(
            any(str(e.get("by", "")).startswith("human:") for e in okf_frontmatter.verifiers(front))
        )
    assert [t == "human-reviewed" for t in tiers] == stamped
    assert "machine-confirmed" in tiers


def test_every_index_gloss_is_its_concepts_description(tmp_path):
    """The generator is refused and the check is adopted, so the check is graded.

    The break lands on a copy, the way the sibling case does. An edit to a
    tracked concept leaves the tree dirty where the run is killed between the
    two writes.
    """
    assert check_index_gloss.check(BUNDLE) == []

    bundle = tmp_path / "knowledge"
    shutil.copytree(BUNDLE, bundle)
    concept = bundle / "defects" / "the-overlay-doubled-its-own-edges.md"
    text = concept.read_text(encoding="utf-8")
    moved = text.replace("A call edge is keyed", "A call edge is now keyed", 1)
    assert moved != text
    concept.write_text(moved, encoding="utf-8")

    findings = check_index_gloss.check(bundle)
    assert len(findings) == 1
    assert "the-overlay-doubled-its-own-edges.md" in findings[0]


OLD = """\
---
type: Decision
resource: src/graphrag/resolve.py
sources:
  - id: fleet-record
    resource: ../references/a-record.md
  - id: spec
    resource: https://example.invalid/SPEC.md
---

body
"""


def test_a_corrected_citation_is_not_a_dropped_source():
    """`okf check` names a dropped source by its resource, so a fixed path reads as a drop.

    The `id` is the stable handle. A resource corrected under a surviving id is
    a correction, and only a lost id is a shrink. The top-level `resource` field
    sits above the list, so the parse must not pair it with the first id.
    """
    assert check_no_shrink._sources(OLD) == [
        ("fleet-record", "../references/a-record.md"),
        ("spec", "https://example.invalid/SPEC.md"),
    ]

    fixed = OLD.replace("../references/a-record.md", "knowledge/references/a-record.md")
    assert check_no_shrink._id_survives(OLD, fixed, "../references/a-record.md")

    dropped = OLD.replace("  - id: spec\n    resource: https://example.invalid/SPEC.md\n", "")
    assert not check_no_shrink._id_survives(OLD, dropped, "https://example.invalid/SPEC.md")
