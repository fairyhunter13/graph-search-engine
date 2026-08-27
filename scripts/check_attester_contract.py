"""Every Attested Computation names an attester that reads every receipt field.

`okfrules` checks `runtime` and the computation XOR and stops there. The
receipt-to-attester invariant is written down upstream and enforced nowhere,
and both live Attested Computations in the fleet point at attesters that were
deleted. A contract naming a missing attester is worse than no contract,
because it reads as attested.

The attester is read with `ast`, never imported. A gate that executes the code
it is grading has graded nothing, and this script runs on whatever the push
carries.

Usage: check_attester_contract.py <bundle-dir>. Exit 1 on any finding.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import yaml

FIELDS_NAME = "RECEIPT_FIELDS"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    _, block, _ = text.split("---\n", 2)
    return yaml.safe_load(block) or {}


def _receipt_fields(path: Path) -> list[str] | None:
    """The attester's declared contract, read without running it."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, ast.AnnAssign)
            else []
        )
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if FIELDS_NAME not in names or not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        if node.value is None:
            return None
        try:
            value = ast.literal_eval(node.value)
        except ValueError:
            return None
        return [str(v) for v in value]
    return None


def check(bundle: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(bundle.rglob("*.md")):
        front = _frontmatter(path)
        if front.get("type") != "Attested Computation":
            continue
        here = path.parent

        executor = front.get("executor") or {}
        run = executor.get("resource")
        if not run or not (here / run).is_file():
            findings.append(f"{path}: executor.resource does not exist: {run!r}")

        attester = (front.get("attester") or {}).get("resource")
        if not attester:
            findings.append(f"{path}: no attester.resource, so the contract reads as attested")
            continue
        target = here / attester
        if not target.is_file():
            findings.append(f"{path}: attester.resource does not exist: {attester!r}")
            continue

        declared = _receipt_fields(target)
        if declared is None:
            findings.append(
                f"{target}: no module-level {FIELDS_NAME}, so nothing declares what it reads"
            )
            continue

        receipt = executor.get("receipt") or []
        if not receipt:
            findings.append(
                f"{path}: executor.receipt is empty, so the run returns nothing to check"
            )
        unread = [f for f in receipt if f not in declared]
        if unread:
            findings.append(f"{path}: the attester never reads {', '.join(unread)}")
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
