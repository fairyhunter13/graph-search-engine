"""The workflow is the only gate a push that skipped the hook still meets.

A floating tag moves under the pin, so the version a run executes is not the
version anyone reviewed.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
PINNED = re.compile(r"^[\w.-]+/[\w.-]+(/[\w.-]+)*@[0-9a-f]{40}$")


def _steps(doc: dict):
    for job in doc["jobs"].values():
        yield from job["steps"]


def test_the_workflow_pins_every_action():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    used = [step["uses"] for step in _steps(doc) if "uses" in step]
    assert used
    assert [u for u in used if not PINNED.match(u)] == []


def test_the_workflow_reads_and_never_writes():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert doc["permissions"] == {"contents": "read"}


def test_no_step_continues_on_error():
    """A step that reports green after failing gates nothing."""
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert [s for s in _steps(doc) if s.get("continue-on-error")] == []


def test_it_runs_on_main_and_by_hand_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    # `on` is the YAML 1.1 boolean `True` after a safe load, and the key is the
    # word in the file.
    triggers = doc.get("on", doc.get(True))
    assert set(triggers) == {"push", "workflow_dispatch"}
    assert triggers["push"]["branches"] == ["main"]
