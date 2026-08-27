"""Every index gloss equals the `description` of the concept it points at.

Upstream generates `index.md` from the concepts, so the two strings cannot
drift. This bundle writes the index by hand, and `okfrules` checks only that
every sibling is listed. So the gloss is one string in two places with nothing
holding them equal, and four entries had already drifted when this was written.

The generator is refused and the check is adopted, because generating the index
means a model call to write six words.

Usage: check_index_gloss.py <bundle-dir>. Exit 1 on any finding.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from okf_frontmatter import frontmatter

ENTRY = re.compile(r"^\*\s+\[(?P<title>.+?)\]\((?P<target>[^)]+)\)\s+-\s+(?P<gloss>.+)$", re.S)


def _entries(index: Path) -> list[tuple[str, str]]:
    """Each bullet as `(target, gloss)`, with a wrapped entry joined first."""
    text = index.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        _, _, text = text.split("---\n", 2)
    out = []
    for block in re.split(r"\n(?=\*\s)", text):
        hit = ENTRY.match(block.strip())
        if hit is not None:
            out.append((hit.group("target"), " ".join(hit.group("gloss").split())))
    return out


def check(bundle: Path) -> list[str]:
    findings: list[str] = []
    for index in sorted(bundle.rglob("index.md")):
        for target, gloss in _entries(index):
            concept = (index.parent / target).resolve()
            if concept.name == "index.md":
                continue
            if not concept.is_file():
                findings.append(f"{index}: the entry points at nothing: {target}")
                continue
            want = str(frontmatter(concept).get("description", "")).strip()
            if not want:
                findings.append(f"{concept}: no description, so the gloss copies nothing")
                continue
            if " ".join(want.split()) != gloss:
                findings.append(f"{index}: the gloss for {target} is not its description")
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} <bundle-dir>", file=sys.stderr)
        return 2
    bundle = Path(argv[1])
    if not bundle.is_dir():
        print(f"no bundle at {bundle}", file=sys.stderr)
        return 2
    findings = check(bundle)
    for line in findings:
        print(line, file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
