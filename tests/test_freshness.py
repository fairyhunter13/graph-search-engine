"""T-287. Save-to-searchable, measured against a running daemon.

No fixture and no hand-run `index_once`. A fixture grades a different code path
from the one a save takes, and the claim is about the save.

The run is opt-in, because it needs a real repository, a real editor-shaped
save, and the daemon holding the writer lock. Name the root and the file:

    GRAPHRAG_FRESHNESS_ROOT=/path/to/repo \\
    GRAPHRAG_FRESHNESS_FILE=internal/thing/thing.go \\
    GRAPHRAG_FRESHNESS_SNIPPET='\\nfunc %s() int { return 1 }\\n' \\
    pytest tests/test_freshness.py

The file's bytes and its mode are restored after every sample and again in a
`finally`, because these are real repositories.
"""

from __future__ import annotations

import json
import os
import sqlite3
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from graphrag import config

NODE_ID = "tests/test_freshness.py::test_a_save_is_searchable_before_the_next_one_lands"

SAMPLES = int(os.environ.get("GRAPHRAG_FRESHNESS_SAMPLES", "12"))
DEADLINE_S = float(os.environ.get("GRAPHRAG_FRESHNESS_DEADLINE_S", "120"))
# One second is the criterion. The band is the criterion plus the room a busy
# fleet needs, and a p99 outside it is a finding rather than a flake.
P50_CEILING_MS = float(os.environ.get("GRAPHRAG_FRESHNESS_P50_CEILING_MS", "1000"))


def _healthz() -> dict | None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/healthz", timeout=5) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _hit(store: Path, name: str) -> bool:
    """Read-only, and a fresh connection each poll. The daemon is the writer."""
    try:
        conn = sqlite3.connect(f"file:{store}?mode=ro", uri=True, timeout=1.0)
    except sqlite3.Error:
        return False
    try:
        row = conn.execute("SELECT count(*) FROM nodes WHERE name = ?", (name,)).fetchone()
        return bool(row and row[0])
    except sqlite3.Error:
        return False
    finally:
        conn.close()


@pytest.mark.slow
def test_a_save_is_searchable_before_the_next_one_lands():
    """The property the watcher hint buys, timed end to end through the daemon.

    A miss is recorded and not swallowed. A sample that never became queryable
    is the reading that matters most, and dropping the row reports it as
    silence.
    """
    raw_root = os.environ.get("GRAPHRAG_FRESHNESS_ROOT", "")
    raw_file = os.environ.get("GRAPHRAG_FRESHNESS_FILE", "")
    if not raw_root or not raw_file:
        pytest.skip("set GRAPHRAG_FRESHNESS_ROOT and GRAPHRAG_FRESHNESS_FILE")

    health = _healthz()
    if health is None or not health.get("worker_alive") or not health.get("watching"):
        pytest.skip("no daemon on 127.0.0.1:8766, or it is not watching")

    root = Path(raw_root).resolve()
    target = root / raw_file
    if not target.is_file():
        pytest.skip(f"no file at {target}")

    store = config.index_path(root)
    if not store.is_file():
        pytest.skip(f"no store at {store}: index the project first")

    snippet = os.environ.get("GRAPHRAG_FRESHNESS_SNIPPET", "\ndef %s():\n    return 1\n")
    original = target.read_bytes()
    mode = target.stat().st_mode

    samples: list[float] = []
    misses = 0
    try:
        for i in range(SAMPLES):
            name = f"ZzFresh{i:03d}"
            start = time.perf_counter()
            # An editor's atomic save: write a temp file, rename over the
            # target, and carry the mode across. `_keep` drops the temp name.
            tmp = target.with_suffix(target.suffix + ".zzfresh.tmp")
            tmp.write_bytes(original + (snippet % name).encode())
            os.chmod(tmp, mode)
            tmp.replace(target)
            deadline = start + DEADLINE_S
            while time.perf_counter() < deadline:
                if _hit(store, name):
                    samples.append((time.perf_counter() - start) * 1000)
                    break
                time.sleep(0.02)
            else:
                misses += 1
            target.write_bytes(original)
            os.chmod(target, mode)
            time.sleep(2.0)
    finally:
        target.write_bytes(original)
        os.chmod(target, mode)

    assert samples, f"no sample became queryable in {DEADLINE_S:.0f} s, over {SAMPLES} saves"
    assert misses == 0, f"{misses} of {SAMPLES} saves never became queryable"

    ordered = sorted(samples)
    p50 = statistics.median(ordered)
    p99 = ordered[min(len(ordered) - 1, round(0.99 * (len(ordered) - 1)))]
    files = _files(store)
    whole_tree_pass_s = _whole_tree_pass_s(root)

    assert p50 <= P50_CEILING_MS, f"p50 {p50:.0f} ms over the {P50_CEILING_MS:.0f} ms criterion"

    _write_receipt(root, files, ordered, misses, p50, p99, whole_tree_pass_s)


def _files(store: Path) -> int:
    conn = sqlite3.connect(f"file:{store}?mode=ro", uri=True, timeout=5.0)
    try:
        return int(conn.execute("SELECT count(*) FROM files").fetchone()[0])
    finally:
        conn.close()


def _whole_tree_pass_s(root: Path) -> float:
    """The before-arm, timed rather than recalled: one unhinted pass, in-process.

    The daemon holds the writer lock, so this is the read half only -- enumerate
    and hash the tree, which is the term the hint removes.
    """
    from graphrag import discover, projcfg

    cfg = projcfg.effective(root)
    start = time.perf_counter()
    discover.enumerate_files(root, exclude=cfg.exclude, languages=cfg.languages)
    return round(time.perf_counter() - start, 4)


def _write_receipt(
    root: Path,
    files: int,
    samples: list[float],
    misses: int,
    p50: float,
    p99: float,
    whole_tree_pass_s: float,
) -> None:
    """The artifact the attester grades. A literal in test source grades nothing.

    This runs after the assertions, so the outcome it records is always a pass.
    """
    with config.receipt_lock(NODE_ID):
        config.write_receipt(
            NODE_ID,
            {
                "test_node_id": NODE_ID,
                "corpus_ref": root.name,
                **config.provenance(Path(__file__).resolve().parent.parent),
                "outcome": "pass",
                "files": files,
                "n_samples": len(samples),
                "misses": misses,
                "edit_to_queryable_ms_p50": round(p50, 1),
                "edit_to_queryable_ms_p99": round(p99, 1),
                "whole_tree_pass_s": whole_tree_pass_s,
            },
        )
