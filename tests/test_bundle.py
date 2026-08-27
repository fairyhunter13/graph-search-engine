"""The knowledge bundle, checked from the repo rather than from the checker.

`okfrules` runs in the gate and grades the bundle against its own rules. These
cases hold the two things the gate cannot see: that the root declares a version
this repo actually targets, and that the timestamp trap upstream documents is
not reachable through this repo's own reader.
"""

from __future__ import annotations

from pathlib import Path

import yaml

BUNDLE = Path(__file__).resolve().parent.parent / "knowledge"


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
