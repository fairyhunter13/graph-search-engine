"""The watcher, the progress file and the ledgers. Real inotify, real files."""

from __future__ import annotations

import threading
import time

import pytest

from graphrag import config, index, ledger, progress, registry, trace, watch

TWO = {
    "a.py": "def alpha():\n    return 1\n",
    "b.py": "def beta():\n    return 2\n",
}


def _drain() -> None:
    while index.QUEUE.take(timeout=0.01) is not None:
        pass


@pytest.fixture
def watching(repo):
    """A claimed project with the watcher running over it."""
    root = repo("watched", TWO)
    registry.claim(root, direct=True)
    _drain()
    # Stop first. Another module's daemon fixture may still hold a live thread,
    # and `start` returns early on one, which would watch that test's roots.
    watch.stop()
    watch._intent = ()
    watch.start()
    for _ in range(200):
        if watch._intent == (root,):
            break
        time.sleep(0.05)
    assert watch.alive(), "the watcher thread never came up"
    assert watch._intent == (root,), "the watcher armed on another test's roots"
    yield root
    watch.stop()
    _drain()


def _wait_for_depth(target: int, seconds: float = 10.0) -> int:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if index.QUEUE.depth >= target:
            break
        time.sleep(0.05)
    return index.QUEUE.depth


def test_single_edit_reparses_one_file(watching):
    """`T-16`: two edits inside the debounce raise one job, never one per file."""
    (watching / "a.py").write_text("def alpha():\n    return 11\n")
    (watching / "b.py").write_text("def beta():\n    return 22\n")
    assert _wait_for_depth(1) == 1
    rows = []
    for _ in range(100):
        rows = ledger.read(ledger.WATCH)
        if rows:
            break
        time.sleep(0.05)
    assert rows, "the watcher wrote no row for an edit it acted on"
    assert list(rows[0]["projects"]) == [str(watching)]


def test_a_file_the_indexer_would_refuse_never_wakes_it(watching):
    """`T-70`: the watcher's filter is the indexer's, so it wakes on nothing else."""
    (watching / "notes.txt").write_text("prose, and no grammar for it")
    (watching / "node_modules").mkdir()
    (watching / "node_modules" / "c.py").write_text("def gamma():\n    return 3\n")
    time.sleep(1.5)
    assert index.QUEUE.depth == 0


def test_rearm_only_when_the_watched_set_moved(watching, repo):
    """`T-71`: an unchanged reconcile leaves the watches in place."""
    watch._rearm.clear()
    watch.rearm_if_changed()
    assert not watch._rearm.is_set()
    registry.claim(repo("second", TWO), direct=True)
    watch.rearm_if_changed()
    assert watch._rearm.is_set()


def test_progress_reports_a_pass_and_then_an_idle(repo):
    """`T-66`: the progress file carries a rate and an eta while a pass runs."""
    root = repo("progressed", TWO)
    progress.begin(root, 2)
    progress.advance()
    time.sleep(0.01)
    progress.advance()
    snapshot = progress.snapshot()
    assert snapshot["files_done"] == 2
    assert snapshot["percent"] == 100.0
    assert snapshot["files_per_s"] > 0
    progress.finish()
    assert progress.read(root)["phase"] == "idle"


def test_an_index_pass_writes_its_progress_file(repo):
    """`T-67`: the file is keyed the way the graph is, so the two agree."""
    root = repo("indexed", TWO)
    index.index_once(root)
    assert progress.path_for(root).parent == config.PROGRESS_DIR
    assert progress.read(root)["project"] == str(root)


def test_the_ledger_rotates_and_still_answers(monkeypatch):
    """`T-68`: a rotation one moment before a question does not empty the answer."""
    monkeypatch.setattr(config, "LEDGER_MAX_BYTES", 200)
    for n in range(20):
        ledger.append(ledger.RUN, {"kind": "index", "root": f"/tmp/{n}"})
    rotated = ledger.path(ledger.RUN).with_suffix(".jsonl.1")
    assert rotated.exists()
    rows = ledger.read(ledger.RUN, limit=50)
    live = len(ledger.path(ledger.RUN).read_text().splitlines())
    assert len(rows) > live, "the rotated generation went unread"
    assert rows[0]["root"] == "/tmp/19"


def test_a_failed_pass_leaves_a_row_and_a_registry_error(repo):
    """`T-69`: the worker records a real failure rather than dying on it.

    A regular file stands where the store directory belongs, so opening the
    graph fails the way it fails on a full or read-only state directory.
    Nothing is stubbed: the pass runs and the write refuses it.
    """
    root = repo("broken", TWO)
    registry.claim(root, direct=True)
    _drain()
    config.INDEX_DIR.parent.mkdir(parents=True, exist_ok=True)
    config.INDEX_DIR.write_text("not a directory")
    index.QUEUE.submit(root)
    stop = threading.Event()
    worker = threading.Thread(target=index.run_worker, kwargs={"stop": stop}, daemon=True)
    worker.start()
    for _ in range(200):
        entry = registry.get(root)
        if entry and entry.last_error:
            break
        time.sleep(0.05)
    stop.set()
    worker.join(timeout=5)

    assert registry.get(root).last_error, "a failed pass left the row clean"
    errors = ledger.read(ledger.RUN, errors_only=True)
    assert errors, "a failed pass wrote no row"
    assert errors[0]["trace"], "a failure row with no trace id cannot be found again"


def test_a_trace_id_reaches_the_error_text():
    """`T-72`: an error a caller can quote back names the row that recorded it."""
    assert trace.stamp("the graph could not be opened") == "the graph could not be opened"
    with trace.span("a1b2c3d4") as trace_id:
        assert trace_id == "a1b2c3d4"
        assert trace.stamp("the graph could not be opened").endswith("[trace a1b2c3d4]")
    assert trace.current() == ""
