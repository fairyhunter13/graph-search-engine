"""The knowledge bundle, checked from the repo rather than from the checker.

`okfrules` runs in the gate and grades the bundle against its own rules. These
cases hold the two things the gate cannot see: that the root declares a version
this repo actually targets, and that the timestamp trap upstream documents is
not reachable through this repo's own reader.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "knowledge"


class FrontmatterLoader(yaml.SafeLoader):
    """The timestamp resolver removed, because YAML 1.1 rewrites one silently.

    `2026-06-30T14:00:00Z` loads as a `datetime` and dumps back as
    `2026-06-30 14:00:00+00:00`, which carries no offset marker any more. A
    reader that round-trips frontmatter therefore disables freshness on the
    first pass and cannot see that it did.
    """


FrontmatterLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in FrontmatterLoader.yaml_implicit_resolvers.items()
}


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    _, block, _ = text.split("---\n", 2)
    return yaml.load(block, Loader=FrontmatterLoader) or {}


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


def test_no_link_in_the_bundle_starts_at_the_root():
    """The spec recommends a leading slash and GitHub renders it as a 404."""
    for path in sorted(BUNDLE.rglob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            assert "](/" not in line, f"{path}: {line}"


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


def test_dropped_receipt_field_fails():
    """A receipt field the attester never reads is a claim nothing checks."""
    contract = ROOT / "scripts" / "check_attester_contract.py"
    spec = importlib.util.spec_from_file_location("check_attester_contract", contract)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.check(BUNDLE) == []

    concept = BUNDLE / "computations" / "import-scoping-collapses-the-candidate-set.md"
    text = concept.read_text(encoding="utf-8")
    broken = text.replace("commit_sha,", "commit_sha, wall_clock_s,")
    assert broken != text
    concept.write_text(broken, encoding="utf-8")
    try:
        findings = module.check(BUNDLE)
    finally:
        concept.write_text(text, encoding="utf-8")
    assert len(findings) == 1
    assert "wall_clock_s" in findings[0]
