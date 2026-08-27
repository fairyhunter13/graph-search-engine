"""Append-only JSONL, one generation of rotation, never read back as state.

Best-effort by construction. A ledger is evidence of what the daemon did, and a
daemon that fails an index pass because a telemetry write failed has traded the
work for the record of it.

Two ledgers, because they are read at different moments. `run` is read when
something did not happen. `watch` is read when something happened too often.
"""

from __future__ import annotations

import contextlib
import json
import time
from pathlib import Path

from . import config, trace

RUN = "run"
WATCH = "watch"


def path(name: str = RUN) -> Path:
    return config.LEDGER_DIR / f"{name}.jsonl"


def append(name: str, row: dict) -> None:
    target = path(name)
    with contextlib.suppress(OSError):
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size >= config.LEDGER_MAX_BYTES:
            target.replace(target.with_suffix(".jsonl.1"))
        # Full precision, not rounded. A millisecond holds many appends, and a
        # tie is what makes "the newest row" ambiguous when the ledger is read.
        stamped = {"ts": time.time(), "trace": trace.current(), **row}
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(stamped, default=str) + "\n")


def read(name: str = RUN, limit: int = 50, *, errors_only: bool = False) -> list[dict]:
    """The newest rows first, across both generations.

    The rotated generation is read too. A rotation one moment before a question
    is asked would otherwise answer it with an empty file.
    """
    rows: list[dict] = []
    target = path(name)
    for source in (target, target.with_suffix(".jsonl.1")):
        with contextlib.suppress(OSError):
            for line in source.read_text(encoding="utf-8").splitlines():
                with contextlib.suppress(ValueError):
                    rows.append(json.loads(line))
    # Sort ascending and reverse, never `reverse=True`. `ts` is rounded to a
    # millisecond, so two rows written in the same one tie, and a stable sort
    # then hands back the older of the pair first.
    rows.sort(key=lambda row: row.get("ts", 0))
    rows.reverse()
    if errors_only:
        rows = [row for row in rows if row.get("error")]
    return rows[:limit]
