"""Both ends of the watch pipe: `arm` in the daemon, `main` in the child.

`RustNotify` holds the GIL while it arms, and arming walks every directory under
every root. In the daemon that stopped every thread, the watchdog pinger among
them: coderag's 110,827 directories held it for 7.7 s at load 12 and past 90 s at
load 27-40. So `watchfiles.watch` runs in `python -m graphrag.watchchild`, where
the walk holds that process's GIL.

stdin carries the roots as one JSON array, and argv carries debounce and timeout
in milliseconds. stdout carries one JSON line per batch, an empty one on every
timeout, and `{"error": ...}` before a failed exit.
"""

from __future__ import annotations

import contextlib
import json
import os
import selectors
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from watchfiles import Change, watch


def arm(
    *roots: Path,
    watch_filter: Callable[[Change, str], bool],
    stop_event: threading.Event,
    debounce: int,
    rust_timeout: int,
    yield_on_timeout: bool,
):
    """`watchfiles.watch` with the same arguments and batches, run in the child.

    `watch_filter` is a closure over the daemon's state, so it runs here, on each
    batch. The child writes an empty batch on every timeout, so `yield_on_timeout`
    must be true. A dead child raises `OSError`, which `watch._loop` re-arms on.
    """
    assert yield_on_timeout, "the child always yields on timeout"
    child = subprocess.Popen(
        [sys.executable, "-m", "graphrag.watchchild", str(debounce), str(rust_timeout)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    try:
        child.stdin.write(json.dumps([str(root) for root in roots]).encode())
        child.stdin.close()
        fd, pending = child.stdout.fileno(), b""
        with selectors.DefaultSelector() as ready:
            ready.register(fd, selectors.EVENT_READ)
            while not stop_event.is_set():
                if b"\n" not in pending:
                    # Short, so `stop` never waits out the child's poll.
                    if ready.select(0.2):
                        chunk = os.read(fd, 1 << 16)
                        if not chunk:
                            raise OSError(f"the watch process exited with status {child.wait()}")
                        pending += chunk
                    continue
                line, pending = pending.split(b"\n", 1)
                batch = json.loads(line)
                if isinstance(batch, dict):
                    raise OSError(batch["error"])
                yield {
                    (Change(change), path)
                    for change, path in batch
                    if watch_filter(Change(change), path)
                }
    finally:
        child.kill()
        child.wait()


def main() -> int:
    debounce, timeout = int(sys.argv[1]), int(sys.argv[2])
    roots = json.load(sys.stdin)
    try:
        for batch in watch(*roots, debounce=debounce, rust_timeout=timeout, yield_on_timeout=True):
            sys.stdout.write(json.dumps([[int(change), path] for change, path in batch]) + "\n")
            sys.stdout.flush()
    except BrokenPipeError:
        return 0
    except Exception as exc:
        with contextlib.suppress(BrokenPipeError):
            sys.stdout.write(json.dumps({"error": f"{type(exc).__name__}: {exc}"}) + "\n")
            sys.stdout.flush()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
