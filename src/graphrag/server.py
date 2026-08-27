"""The daemon: three routes, one worker thread, and an exit that skips finalization.

`/healthz`, `/register` and `/mcp`. `/register` is the route no model calls: a
SessionStart hook enrols the directory it opens in, and nothing else here can
create a registry row without a model asking for it.

Two lifecycle facts, both inherited from the sibling engine rather than
rediscovered. The stop path calls `os._exit(0)`, because a clean interpreter
shutdown runs `atexit` against a half-closed event loop and hangs, and systemd
then kills the unit on a timeout and fires `OnFailure` on every deliberate stop.
Reaching that exit needs `timeout_graceful_shutdown`: streamable HTTP holds its
connections open, so uvicorn otherwise waits on clients that never disconnect.
"""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import socket
import threading
from collections.abc import AsyncIterator

import anyio.to_thread
import uvicorn
from starlette.responses import JSONResponse

from . import config, index, registry, watch
from .tools import enroll, mcp

log = logging.getLogger(__name__)

_worker: threading.Thread | None = None
_stop = threading.Event()


def _notify(state: str) -> None:
    """sd_notify without the systemd binding, which is a C extension."""
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    with contextlib.suppress(OSError), sock:
        sock.connect("\0" + addr[1:] if addr.startswith("@") else addr)
        sock.sendall(state.encode())


def _start_worker() -> None:
    global _worker
    if _worker is not None and _worker.is_alive():
        return
    _stop.clear()
    _worker = threading.Thread(
        target=index.run_worker, kwargs={"stop": _stop}, name="indexer", daemon=True
    )
    _worker.start()


@contextlib.asynccontextmanager
async def lifespan(_app) -> AsyncIterator[None]:
    """READY comes after the queue is served, not before.

    `Type=notify` is what makes the first session's tool call wait for a daemon
    that can answer. Announcing ready before the worker runs means a call lands
    on a process that accepts it and does nothing with it.
    """
    _start_worker()
    watch.start()
    rows = registry.load()
    queued = sum(
        1 for path, row in rows.items() if row.enabled and index.QUEUE.submit(path) == "queued"
    )
    log.info("ready: %d projects queued", queued)
    _notify("READY=1")
    try:
        yield
    finally:
        _notify("STOPPING=1")
        watch.stop()
        _stop.set()


async def register(request) -> JSONResponse:
    """Enrol a directory whose caller is standing in it, with no model in the loop.

    The `index` tool cannot serve this. A SessionStart hook speaks plain HTTP and
    carries no MCP client roots, so it has no way to call a tool at all.
    """
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "the body is not JSON"}, status_code=400)
    root = (body or {}).get("root")
    if not root:
        return JSONResponse({"error": "the body names no root"}, status_code=400)
    # Off the event loop: enrolment resolves a path and reads the store, and
    # `/healthz` answers behind it otherwise.
    return JSONResponse(await anyio.to_thread.run_sync(enroll, root))


async def healthz(_request) -> JSONResponse:
    rows = registry.load()
    failing = sorted(k for k, e in rows.items() if e.enabled and e.last_error)
    return JSONResponse(
        {
            "status": "ok",
            "projects": sum(1 for e in rows.values() if e.enabled),
            # Identities, not only the count. A checker deciding "still failing"
            # compares the same projects across two runs, and a count cannot tell
            # one project failing twice from two failing once each.
            "projects_failing": len(failing),
            "failing": failing,
            "queue_depth": index.QUEUE.depth,
            "worker_alive": bool(_worker and _worker.is_alive()),
            # The watcher is the one failure no project row can carry: it
            # belongs to the thread, not to a project, and a dead one reads as
            # a fleet that simply stopped changing.
            "watching": watch.alive(),
            "fleet_digest": registry.fleet_digest(rows),
            "unclaimed_stores": len(registry.unclaimed_stores()),
        }
    )


def build_app():
    # Stateless: a fresh transport per request and no session id to carry. This
    # daemon has no subscriptions and no sampling, so there is nothing for a
    # session to hold.
    app = mcp.streamable_http_app(stateless_http=True)
    served = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def both(scope) -> AsyncIterator[None]:
        # Nested, never replaced. The SDK lifespan is what enters the session
        # manager's task group, and assigning over it leaves every `/mcp` call
        # answering 500 while `/healthz` stays green.
        async with served(scope), lifespan(scope):
            yield

    app.router.lifespan_context = both
    app.add_route("/healthz", healthz, methods=["GET"])
    app.add_route("/register", register, methods=["POST"])
    return app


def port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def serve(host: str = "", port: int = 0) -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    host, port = host or config.HOST, port or config.PORT
    # The port is fixed and documented. A silent rebind leaves every registered
    # client pointing at nothing and looking correct while it does so, and the
    # first URL the installer seeds into the five profiles is permanent.
    if not port_free(host, port):
        raise SystemExit(f"port {port} on {host} is already in use, so the daemon will not start")
    # `Terminating session: None` once per request, with no session id to name
    # under stateless HTTP. A level rather than a filter: a filter keyed on the
    # message breaks in silence at the next SDK release.
    logging.getLogger("mcp.server.streamable_http").setLevel(logging.WARNING)
    # uvicorn restores the handler it replaced and re-raises the signal it
    # caught, so the exit below is unreachable unless ours is what it restores.
    signal.signal(signal.SIGTERM, lambda *_: _exit())
    uvicorn.run(
        build_app(),
        host=host,
        port=port,
        log_level="info",
        access_log=False,
        timeout_graceful_shutdown=5,
    )
    _exit()


def _exit() -> None:
    log.info("exiting")
    for stream in (1, 2):
        with contextlib.suppress(OSError):
            os.fsync(stream)
    os._exit(0)
