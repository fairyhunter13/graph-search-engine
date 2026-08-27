"""The two-sample rule, against a real HTTP server serving a real body.

Nothing is stubbed: `check` opens a socket and reads JSON off it, the way it
does against the daemon. What the body says is the only thing these cases vary.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from graphrag import health

OK = {"status": "ok", "projects": 3, "projects_failing": 0, "failing": [], "queue_depth": 0}


class _State:
    body: ClassVar[dict] = dict(OK)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = json.dumps(_State.body).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        return


@pytest.fixture
def healthz():
    """A live `/healthz`, and a setter for what it answers."""
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/healthz"

    def say(**fields) -> str:
        _State.body = {**OK, **fields}
        return url

    yield say
    server.shutdown()
    thread.join(timeout=5)


def test_two_sample_rule(healthz, state_dir):
    """`T-17`: a project pages at the second failure, never at the first."""
    url = healthz(projects_failing=1, failing=["/srv/one"])
    state = state_dir / "health.json"

    ok, reason = health.check(url, state)
    assert ok, reason
    assert "first time" in reason

    ok, reason = health.check(url, state)
    assert not ok
    assert "/srv/one" in reason
    assert "since the last check" in reason


def test_a_healed_project_stops_paging(healthz, state_dir):
    """`T-73`: the next success clears the row, so the identity leaves the set."""
    state = state_dir / "health.json"
    url = healthz(projects_failing=1, failing=["/srv/one"])
    health.check(url, state)
    health.check(url, state)

    ok, reason = health.check(healthz(), state)
    assert ok
    assert "none failing" in reason


def test_a_dead_worker_pages_though_no_project_is_failing(healthz, state_dir):
    """`T-74`: up and not indexing is the failure no project row can carry."""
    state = state_dir / "health.json"
    url = healthz(worker_alive=False)
    ok, first = health.check(url, state)
    assert ok
    assert "worker thread" in first

    ok, second = health.check(url, state)
    assert not ok
    assert "the worker thread is not running" in second


def test_a_stalled_queue_pages_at_the_stall(healthz, state_dir):
    """`T-75`: the queue carries two samples of its own, so the rule runs once."""
    state = state_dir / "health.json"
    health.check(healthz(queue_depth=40), state)
    ok, reason = health.check(healthz(queue_depth=40), state)
    assert not ok
    assert "the queue is not draining" in reason


def test_an_unreachable_daemon_is_reported_not_ranked(state_dir):
    """`T-76`: no answer is the graph being unavailable, not a project failing."""
    ok, reason = health.check("http://127.0.0.1:1/healthz", state_dir / "health.json")
    assert not ok
    assert "did not answer" in reason
