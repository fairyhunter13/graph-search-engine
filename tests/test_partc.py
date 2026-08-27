"""Part C's four unsupported claims, graded against the receipts.

An audit read fourteen verification bullets and found four with no evidence
under them. Each of the four rests on something only this machine holds: the
two SessionStart hooks, the user units, the five profile files and the port the
daemon owns. A synthetic stand-in for any of them grades itself.

So the shape is the one `tests/test_probe.py` already uses.
`scripts/partc_probe.py` runs the real thing and writes a receipt, and every
case here reads that receipt. A missing receipt is a skip, because a machine
with no daemon and no fleet install cannot take the reading, and a skip is the
honest answer where a pass would be a lie.
"""

from __future__ import annotations

import json

import pytest

from graphrag import config

ARMS = {
    "partc-reach-counts": "reach",
    "partc-notify-order": "notify",
    "partc-five-profiles": "profiles",
    "partc-port-refusal": "port",
}


def _receipt(name: str) -> dict:
    path = config.RECEIPT_DIR / f"{name}.json"
    if not path.is_file():
        arm = ARMS[name]
        pytest.skip(f"no receipt at {path}: run `uv run python scripts/partc_probe.py {arm}`")
    return json.loads(path.read_text(encoding="utf-8"))


def test_both_reach_notices_appear_together():
    """T-200. One session start, and both engines announce themselves."""
    receipt = _receipt("partc-reach-counts")
    for entry in receipt["notices"].values():
        assert entry["exit_code"] == 0, entry
        assert entry["present"], entry
    assert receipt["both_present"], receipt["notices"]


def test_the_graph_notice_reports_what_the_graphrag_cli_reports():
    """T-201. The notice is read out of the live graph, never carried forward.

    A stale count reads as a working engine, so the two numbers are compared
    field by field rather than as a single verdict.
    """
    engine = _receipt("partc-reach-counts")["engines"]["graphrag"]
    notice, cli = engine["notice"], engine["cli"]
    assert notice, "the notice named no node and edge count"
    assert notice["nodes"] == cli["nodes"], engine
    assert notice["edges"] == cli["edges"], engine
    assert notice["resolved_pct"] == cli["resolved_pct"], engine
    assert engine["matches"]


def test_the_code_notice_reports_what_the_coderag_cli_reports():
    """T-202. The sibling engine's own count, and this repo's row in it."""
    engine = _receipt("partc-reach-counts")["engines"]["coderag"]
    notice, cli = engine["notice"], engine["cli"]
    assert notice, "the notice named no file and chunk count"
    assert notice["files"] == cli["files"], engine
    assert notice["chunks"] == cli["chunks"], engine
    assert engine["matches"]


def test_a_clean_stop_precedes_the_start_that_is_timed():
    """T-203. The stop is evidence, because a restart grades the old instance.

    An outgoing daemon can still hold the port while the new one binds. So the
    port has to be free and healthz has to refuse before the start is timed,
    and the machine has to be handed back a daemon that runs.
    """
    receipt = _receipt("partc-notify-order")
    stop = receipt["stop"]
    assert stop["exit_code"] == 0, stop
    assert stop["state_after"] != "active", stop
    assert stop["port_free_after_stop"], stop
    assert stop["healthz_while_stopped"]["status"] == 0, stop

    start = receipt["start"]
    assert start["exit_code"] == 0, start
    assert start["reached_active"], start
    assert json.loads(receipt["healthz_answered"]["body"])["status"] == "ok"
    assert receipt["left_running"], "the probe has to hand the machine back a running daemon"


def test_the_unit_reports_active_only_once_healthz_answers():
    """T-204. The ordering `Type=notify` is supposed to buy.

    One attempt on the first `active` sample, never a retry. A retry proves the
    daemon answers eventually, and the claim is that it answers already.

    This failed on two of four starts while `serve` let uvicorn bind, because
    uvicorn runs lifespan startup first and `READY=1` is sent from there.
    `server.listen` now binds ahead of the lifespan, so the socket exists before
    systemd is told anything.
    """
    receipt = _receipt("partc-notify-order")
    assert receipt["answers_on_first_active_sample"], {
        "healthz": receipt["healthz_on_first_active_sample"],
        "seconds_from_active_to_answer": receipt["seconds_from_active_to_answer"],
    }


def test_the_five_real_profiles_carry_one_graphrag_entry():
    """T-205. The files on this machine, and not five written into a temp dir."""
    receipt = _receipt("partc-five-profiles")
    assert len(receipt["profiles"]) == 5, receipt["profiles"]
    for row in receipt["profiles"]:
        assert row["exists"], row
        assert row.get("has_graphrag"), row
        assert row.get("transport") == "http", row
    assert len({row["url"] for row in receipt["profiles"]}) == 1, receipt["profiles"]

    decoy = receipt["decoy"]
    assert decoy["read_by_a_launcher"] is False
    assert decoy["path"] not in {row["path"] for row in receipt["profiles"]}


def test_the_url_the_profiles_name_answers():
    """T-206. A named URL is a claim until something answers on it."""
    receipt = _receipt("partc-five-profiles")
    assert receipt["urls"], "no profile named a URL, so nothing was called"
    for url, answer in receipt["answers"].items():
        assert answer["mcp_initialize"]["status"] == 200, (url, answer["mcp_initialize"])
        assert '"result"' in answer["mcp_initialize"]["body"], (url, answer["mcp_initialize"])
        assert answer["healthz"]["status"] == 200, (url, answer["healthz"])
        assert '"status":"ok"' in answer["healthz"]["body"], (url, answer["healthz"])


def test_a_taken_port_is_refused_by_name():
    """T-207. Both arms, because one of them cannot be taken any more.

    The plan claimed 8766 was free before the first apply, and the daemon owns
    the port now, so nobody can take that reading again. What is checkable
    today is the invariant behind it: a taken port is a refusal naming the
    port, never a silent rebind that leaves five profiles pointing at nothing.
    """
    receipt = _receipt("partc-port-refusal")
    for arm in (receipt["scratch"], receipt["live"]):
        assert arm["refused"], arm
        assert arm["exit_code"] != 0, arm
        assert arm["names_the_port"], arm
    assert receipt["scratch_free_after_release"], receipt["scratch"]
    assert receipt["live"]["port"] == config.PORT
    assert receipt["daemon_still_answers"]["status"] == 200, receipt["daemon_still_answers"]
    assert receipt["unit_state"] == "active", "the probe must not disturb the running unit"
