"""One file per project, polled by the CLI. Never a protocol notification.

MCP progress attaches to a live request, and background indexing has none. That
is what lets the `index` tool return immediately and still report: the caller
polls a file the worker keeps writing.

A file per project rather than one file for the daemon. The worker serves one
project at a time, so a single file answers "what is happening now" and loses
"how did the project I asked about get on", which is the question a poller has.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import config


@dataclass(slots=True)
class Progress:
    project: str = ""
    phase: str = "idle"
    done: int = 0
    total: int = 0
    # None rather than 0.0, because a zero timestamp is a time in 1970 and a
    # reader comparing it against now reports 56 years of elapsed work.
    started_at: float | None = None
    updated_at: float = 0.0
    pid: int = field(default_factory=os.getpid)


_state = Progress()
_last_write = 0.0


def path_for(project: Path | str) -> Path:
    """Keyed the way the graph is, so the two never disagree about a project."""
    store = config.index_path(project)
    return config.PROGRESS_DIR / f"{store.parent.name}.json"


def begin(project: Path | str, total: int, phase: str = "parsing") -> None:
    global _state
    now = time.time()
    _state = Progress(
        project=str(Path(project).resolve()),
        phase=phase,
        total=int(total),
        started_at=now,
        updated_at=now,
    )
    _write(force=True)


def advance(n: int = 1) -> None:
    _state.done += n
    _state.updated_at = time.time()
    _write()


def phase(name: str) -> None:
    _state.phase = name
    _state.updated_at = time.time()
    _write(force=True)


def finish() -> None:
    _state.phase = "idle"
    _state.updated_at = time.time()
    _write(force=True)


def snapshot(state: Progress | None = None) -> dict:
    current = state or _state
    if current.started_at is None:
        return {}
    elapsed = max(current.updated_at - current.started_at, 0.0)
    out = {
        "project": current.project,
        "phase": current.phase,
        "files_done": current.done,
        "files_total": current.total,
        "elapsed_s": round(elapsed, 1),
        "pid": current.pid,
        "updated_at": current.updated_at,
    }
    if current.total:
        out["percent"] = round(100.0 * current.done / current.total, 1)
    if current.done and elapsed > 0:
        out["files_per_s"] = round(current.done / elapsed, 3)
        out["eta_s"] = round(max(current.total - current.done, 0) * elapsed / current.done, 1)
    return out


def read(project: Path | str) -> dict:
    """What is on disk. `phase` means something only beside `updated_at`.

    A worker killed mid-pass leaves its last line saying `parsing` forever.
    Liveness is the reader's call, from `updated_at` and `pid`.
    """
    try:
        return json.loads(path_for(project).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(force: bool = False) -> None:
    global _last_write
    now = time.time()
    # A terminal write bypasses the throttle. The last write is the one a reader
    # needs most, and throttling it away leaves a finished pass reading as busy.
    if not force and now - _last_write < config.PROGRESS_WRITE_S:
        return
    _last_write = now
    if not _state.project:
        return
    target = path_for(_state.project)
    # Telemetry: a full disk must never fail the index pass it reports on.
    with contextlib.suppress(OSError):
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(snapshot()), encoding="utf-8")
        tmp.replace(target)
