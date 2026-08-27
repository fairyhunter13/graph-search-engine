"""The daemon and the stdio bridge, against a real listening socket.

No mocks: the bridge case runs the shipped console script as a subprocess and
speaks JSON-RPC to a uvicorn server on a real port. A bridge tested against a
fake server proves the fake, and the pipe is the only thing it does.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time

import pytest
import uvicorn

from graphrag import server

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_port_collision_names_the_port():
    """`T-21`: a bound port is an error at startup, never a silent rebind.

    The first URL the installer seeds into the five profiles is permanent, so a
    daemon that quietly moves leaves every client pointing at nothing while
    every config file still reads correct.
    """
    port = _free_port()
    with socket.socket() as held:
        held.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        held.bind(("127.0.0.1", port))
        held.listen(1)
        assert server.port_free("127.0.0.1", port) is False
        with pytest.raises(SystemExit) as caught:
            server.serve(host="127.0.0.1", port=port)
    assert str(port) in str(caught.value)
    assert server.port_free("127.0.0.1", port) is True


@pytest.fixture
def daemon(state_dir):
    """A real daemon on an ephemeral port, stopped by the fixture teardown."""
    port = _free_port()
    running = uvicorn.Server(
        uvicorn.Config(server.build_app(), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=running.run, daemon=True)
    thread.start()
    for _ in range(200):
        if running.started:
            break
        time.sleep(0.05)
    assert running.started, "the daemon never came up"
    yield f"http://127.0.0.1:{port}/mcp"
    running.should_exit = True
    thread.join(timeout=10)


def test_the_bridge_round_trips_one_call(daemon):
    """`T-61`: a line in on stdin is one line of JSON-RPC out on stdout."""
    proc = subprocess.run(
        [sys.executable, "-m", "graphrag.cli", "bridge", "--url", daemon, "--idle", "20"],
        input=json.dumps(INITIALIZE) + "\n",
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    # The daemon answers `initialize` over SSE, so the body carries a `data:`
    # frame. The bridge does not unwrap it, and that is the point: interpreting
    # the protocol is a second implementation of it.
    payload = proc.stdout.strip()
    assert '"result"' in payload
    assert "graphrag" in payload


def test_the_bridge_survives_an_unreachable_daemon():
    """`T-62`: a transport failure goes to stderr, never onto the framed stream."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "graphrag.cli",
            "bridge",
            "--url",
            f"http://127.0.0.1:{_free_port()}/mcp",
            "--idle",
            "20",
        ],
        input=json.dumps(INITIALIZE) + "\n",
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    # One diagnostic line on stdout desynchronises the client for the rest of
    # the session, so an empty stdout is the correct answer to a dead daemon.
    assert proc.stdout.strip() == ""
    assert "bridge:" in proc.stderr
