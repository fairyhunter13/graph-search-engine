"""The two headless receipts, graded against the claims that rest on them.

`J-07` and part B were both self-reported once. `D-21` closed that shape for
the measurements, and it closes it here: the claim is graded against the
receipt `scripts/headless_probe.py` wrote out of the session's own stream.

Both cases skip where the receipt is absent, because a headless session needs
the daemons and the fleet install. A skip is the honest answer. A literal
standing in for the run would grade itself.
"""

from __future__ import annotations

import json

import pytest

from graphrag import config


def _receipt(name: str) -> dict:
    path = config.RECEIPT_DIR / f"{name}.json"
    if not path.is_file():
        pytest.skip(f"no receipt at {path}: run `uv run python scripts/headless_probe.py`")
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_two_questions_reach_the_engines_in_order():
    """T-127. Widen, then confirm, and neither prompt names an engine."""
    receipt = _receipt("j07-routing-selection")
    sessions = {s["shape"]: s for s in receipt["sessions"]}
    for session in sessions.values():
        assert not session["names_an_engine"], session["prompt"]

    meaning = sessions["meaning"]["engines_in_order"]
    assert meaning, "the meaning question reached no engine"
    assert "coderag" in meaning[0], meaning

    # The order is the claim, so the caller arm is read as a sequence. A graph
    # call first would be a session guessing the symbol it was handed.
    caller = sessions["caller"]["engines_in_order"]
    assert "coderag" in caller[0], caller
    assert any("graphrag" in call for call in caller[1:]), caller


def test_the_plan_skill_is_selected_where_it_is_earned():
    """T-128. Both arms, because one answer does not read.

    The skill refuses a repo whose work fits in one issue. So a session that
    skips it on the one-file service obeyed the skill, and only the second arm
    is evidence that the skill can ever be selected.
    """
    receipt = _receipt("partb-skill-dispatch")
    assert not receipt["names_a_skill"], receipt["prompt"]
    sessions = {s["shape"]: s for s in receipt["sessions"]}

    earned = sessions["ingest"]["skills_dispatched"]
    assert "Skill(test-plan)" in earned, earned
    assert "Skill(test-plan)" not in sessions["svc"]["skills_dispatched"]
