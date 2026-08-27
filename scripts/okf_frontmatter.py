"""One reader for OKF frontmatter, and the trust tier the spec derives from it.

Two readers existed. A test carried the loader with the YAML 1.1 timestamp
resolver stripped, and the shipped gate called plain `yaml.safe_load`, which is
the trap: `2026-06-30T14:00:00Z` loads as a `datetime` and dumps back as
`2026-06-30 14:00:00+00:00`, a form `is_stale` then refuses to read. The gate
carried the trap and the test held the fix, so this module is the one reader
both use.

Section 5.3 derives trust from `verified` alone. Section 11 makes a bare
`verified: { by, at }` mapping read identically to a one-element list, and that
is one line of code to get wrong.

Never uses an LLM. Never makes network calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

UNVERIFIED = "unverified"
MACHINE_CONFIRMED = "machine-confirmed"
HUMAN_REVIEWED = "human-reviewed"

HUMAN_PREFIX = "human:"


class FrontmatterLoader(yaml.SafeLoader):
    """The timestamp resolver removed, because YAML 1.1 rewrites one silently.

    A reader that round-trips frontmatter through the stock loader disables
    freshness on the first pass and cannot see that it did.
    """


FrontmatterLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in FrontmatterLoader.yaml_implicit_resolvers.items()
}


def loads(block: str) -> dict:
    """Parse a frontmatter block, timestamps left as the author wrote them."""
    return yaml.load(block, Loader=FrontmatterLoader) or {}


def frontmatter(path: Path) -> dict:
    """The frontmatter of one concept, or an empty mapping where it has none."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    _, block, _ = text.split("---\n", 2)
    return loads(block)


def verifiers(front: dict) -> list[dict]:
    """Every verification event, in both shapes section 11 allows."""
    events: Any = front.get("verified")
    if events is None:
        return []
    if isinstance(events, dict):
        return [events]
    return [event for event in events if isinstance(event, dict)]


def trust_tier(front: dict) -> str:
    """Section 5.3, lowest to highest, from `verified` and nothing else."""
    events = verifiers(front)
    if not events:
        return UNVERIFIED
    for event in events:
        if str(event.get("by", "")).startswith(HUMAN_PREFIX):
            return HUMAN_REVIEWED
    return MACHINE_CONFIRMED
