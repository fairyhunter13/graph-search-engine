"""The units as text, and the enrolment a session opens with.

`systemctl` is never run here. What the units say is this module's contract, and
the ordering they depend on is asserted against the daemon itself in the reach
cases below, against a real HTTP server.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from graphrag import reach, registry, systemd

SRC = {"a.py": "def alpha():\n    return 1\n"}

INDEXED = {
    "root": "/srv/one",
    "files": 12,
    "nodes": 340,
    "edges": 512,
    "resolved": 401,
    "capabilities": {"python": ["calls", "defs"], "c": ["defs"]},
}


class _State:
    body: ClassVar[dict] = dict(INDEXED)
    seen: ClassVar[list] = []


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length") or 0)
        _State.seen.append(json.loads(self.rfile.read(length) or b"{}"))
        payload = json.dumps(_State.body).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        return


@pytest.fixture
def daemon():
    """A live `/register`, and a setter for what it answers."""
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _State.seen = []
    url = f"http://127.0.0.1:{server.server_port}/register"

    def say(body: dict | None = None) -> str:
        _State.body = dict(INDEXED) if body is None else body
        return url

    yield say
    server.shutdown()
    thread.join(timeout=5)


def test_notify_after_store_open(tmp_path):
    """`T-26`: the unit reports started only when the daemon says READY."""
    written = systemd.write(tmp_path, binary="/opt/graphrag/bin/graphrag")
    assert {path.name for path in written} == set(systemd.units())

    service = (tmp_path / systemd.SERVICE).read_text()
    assert "Type=notify" in service, "started must mean answerable, not forked"
    assert "ExecStart=/opt/graphrag/bin/graphrag serve" in service
    assert "Restart=on-failure" in service
    assert "TimeoutStopSec=20" in service
    assert "OnFailure=graphrag-alert@%n.service" in service
    # Two indexers share this machine with the editor, so the second one caps.
    assert "MemoryHigh=2G" in service

    doctor = (tmp_path / systemd.DOCTOR).read_text()
    assert "SuccessExitStatus=0 1" in doctor, "a finding is not a unit failure"
    assert "Persistent=true" in (tmp_path / systemd.DOCTOR_TIMER).read_text()
    assert "OnUnitActiveSec=3600s" in (tmp_path / systemd.HEALTH_TIMER).read_text()
    assert "ExecStartPre=/bin/sleep 8" in (tmp_path / systemd.ALERT).read_text()


def test_only_the_three_named_units_are_enabled():
    """A timer's own service is started by the timer, never enabled by name."""
    assert systemd.ENABLE == (systemd.SERVICE, systemd.HEALTH_TIMER, systemd.DOCTOR_TIMER)
    assert systemd.HEALTH not in systemd.ENABLE
    assert systemd.DOCTOR not in systemd.ENABLE


def test_the_units_are_removed_by_name(tmp_path, monkeypatch):
    """Uninstall removes what this module wrote and touches nothing else."""
    systemd.write(tmp_path, binary="/opt/graphrag/bin/graphrag")
    stranger = tmp_path / "someone-elses.service"
    stranger.write_text("[Unit]\n")
    monkeypatch.setattr(systemd, "_systemctl", lambda *_a: (0, ""))

    answer = systemd.uninstall(tmp_path)
    assert len(answer["removed"]) == len(systemd.units())
    assert stranger.exists(), "uninstall removed a unit it did not write"


def test_reach_registers_the_root(daemon, repo):
    """`T-27`: the hook enrols the directory it stands in, over plain HTTP."""
    root = repo("session", SRC)
    said = reach.notice(root, url=daemon())

    assert _State.seen == [{"root": str(registry.resolve(root))}]
    assert "340 nodes" in said
    assert "401 of them resolved" in said


def test_the_notice_names_the_languages_that_answer_nothing(daemon, repo):
    """A language with no call capture is named up front, not met as silence."""
    said = reach.notice(repo("session", SRC), url=daemon())
    assert "caller questions are answered for python" in said
    assert "c emit no call capture" in said
    assert "not an absence" in said


def test_an_enrolled_but_unindexed_root_says_so(daemon, repo):
    """A queued pass is not an empty graph, and the notice keeps them apart."""
    said = reach.notice(repo("session", SRC), url=daemon({"root": "/srv/one", "queued": "queued"}))
    assert "a pass is queued" in said
    assert "not answerable yet" in said


def test_an_unreachable_daemon_refuses_rather_than_reports_nothing(repo):
    """The variant that matters: unavailable never reads as nothing calls it."""
    said = reach.notice(repo("session", SRC), url="http://127.0.0.1:1/register")
    assert "did not answer" in said
    assert "unavailable" in said
    assert "nothing calling the symbol" in said
