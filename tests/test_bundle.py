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


_RUN_WORDS = (  # noqa: SIM905 -- the literal list this asks for costs 21 lines and reads worse
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty"
).split()


def test_the_arm_list_counts_agree_with_the_number_it_states():
    """`T-337`. The tally three audits each corrected by hand, and no gate saw.

    `40690e6` shipped "Ten runs" against eleven figures in each arm. Nothing
    grades a number written in prose, so a wrong one survives every gate here
    and is found only by a reader who recounts it.

    The sha list is deliberately not counted: one early run's hex is lost, and
    the paragraph names other commits inside the same span.
    """
    text = (BUNDLE / "computations" / "the-graph-answers-the-caller-question.md").read_text(
        encoding="utf-8"
    )
    stated = re.search(r"\b(\w+) runs span\b", text)
    assert stated, "the arm paragraph no longer states a run count"
    said = _RUN_WORDS.index(stated.group(1).lower())

    counts = {}
    for arm in ("lexical", "semantic"):
        listed = re.search(rf"gave ([\d.,\s and]+) {arm}", text)
        assert listed, f"the arm paragraph no longer lists {arm} figures"
        counts[arm] = len(re.findall(r"\d\.\d+", listed.group(1)))
    assert counts == {"lexical": said, "semantic": said}
