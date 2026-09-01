"""The watcher, the progress file and the ledgers. Real inotify, real files."""

from __future__ import annotations

import shutil
import threading
import time

import pytest

from graphrag import config, index, jobs, ledger, progress, prune, registry, trace, watch

TWO = {
    "a.py": "def alpha():\n    return 1\n",
    "b.py": "def beta():\n    return 2\n",
}


def _drain() -> None:
    jobs.QUEUE.drain()


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
        if jobs.QUEUE.depth >= target:
            break
        time.sleep(0.05)
    return jobs.QUEUE.depth


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


def test_a_further_save_restarts_the_quiet_window(tmp_path):
    """`T-214`: a pass runs once the person stops typing, never once per save."""
    queue = jobs.Queue()
    queue.submit(tmp_path, delay=0.3)
    time.sleep(0.2)
    queue.submit(tmp_path, delay=0.3)
    # This take runs out past the first countdown, so a job it returned would be
    # one the second save should have pushed back.
    assert queue.take(timeout=0.2) is None
    assert queue.take(timeout=1.0) == str(tmp_path.resolve())


def test_an_explicit_call_pulls_a_waiting_job_forward(tmp_path):
    """`T-215`: a caller wanting the tree now is not held by someone else's countdown."""
    queue = jobs.Queue()
    assert queue.submit(tmp_path, delay=30) == "queued"
    assert queue.take(timeout=0.05) is None
    assert queue.submit(tmp_path) == "dropped"
    assert queue.take(timeout=1.0) == str(tmp_path.resolve())


def test_a_file_the_indexer_would_refuse_never_wakes_it(watching):
    """`T-70`: the watcher's filter is the indexer's, so it wakes on nothing else."""
    (watching / "notes.txt").write_text("prose, and no grammar for it")
    (watching / "node_modules").mkdir()
    (watching / "node_modules" / "c.py").write_text("def gamma():\n    return 3\n")
    time.sleep(1.5)
    assert jobs.QUEUE.depth == 0


def test_rearm_only_when_the_watched_set_moved(watching, repo):
    """`T-71`: an unchanged reconcile leaves the watches in place."""
    watch._rearm.clear()
    watch.rearm_if_changed()
    assert not watch._rearm.is_set()
    registry.claim(repo("second", TWO), direct=True)
    watch.rearm_if_changed()
    assert watch._rearm.is_set()


def test_a_row_written_by_another_process_reaches_the_watch_set(watching, repo):
    """A project enrolled outside the daemon is watched, with nothing called.

    `graphrag index` runs in the operator's own process and writes the registry
    there. Until 2026-08-30 the daemon re-read that file only after a prune, so
    a row added this way was watched only after a restart: its changes were
    never indexed and its deletion was never seen.

    The negative arm is the absence of any `watch` call below. Against the old
    loop `_intent` never moves and this waits out the full ten seconds.
    """
    second = repo("enrolled-elsewhere", TWO)
    registry.claim(second, direct=True)

    deadline = time.time() + 10.0
    while time.time() < deadline:
        if second in watch._intent:
            break
        time.sleep(0.05)
    assert second in watch._intent, "a row the daemon did not write never reached the watch set"


def test_an_unmoved_registry_is_stat_ed_and_not_parsed(watching):
    """The tick runs once a second, so the guard is what makes it affordable.

    `_stamp` holds the file's mtime and size. A second call over an unchanged
    file must return on that pair alone, which is one `stat` against a parse of
    every row.
    """
    watch.rearm_if_changed()
    stamp = watch._stamp
    assert stamp is not None

    unreadable = config.REGISTRY_PATH.with_suffix(".moved")
    config.REGISTRY_PATH.rename(unreadable)
    try:
        # A parse here raises. Returning quietly proves the stat short-circuited.
        watch.rearm_if_changed()
        assert watch._stamp == stamp
    finally:
        unreadable.rename(config.REGISTRY_PATH)


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
    jobs.QUEUE.submit(root)
    stop = threading.Event()
    worker = threading.Thread(target=jobs.run_worker, kwargs={"stop": stop}, daemon=True)
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


def _run_loop(monkeypatch, fake) -> None:
    """Drive `watch._loop` synchronously against a scripted `watchfiles.watch`."""
    monkeypatch.setattr(watch, "_watch", fake)
    watch._stop.clear()
    watch._rearm.clear()
    watch._intent = ()
    watch._stamp = None
    watch._loop()


def test_a_deletion_is_not_lost_to_a_rearm_queued_in_the_same_pass(repo):
    """`rearm_if_changed` runs inside the loop, so the break it sets lands on the
    batch carrying the deletion. Noting the deletion after that break drops it,
    and inotify has no replay to hand it back.
    """
    doomed = repo("vanishing", TWO)
    keeper = repo("staying", TWO)
    registry.claim(doomed, direct=True)
    registry.claim(keeper, direct=True)
    _drain()
    passes = []

    def fake(*roots, **_kw):
        passes.append(roots)
        if len(passes) > 1:
            watch._stop.set()
            return
        shutil.rmtree(doomed)
        watch._rearm.set()  # what `rearm_if_changed()` does mid-pass
        yield {(3, str(doomed))}  # Change.deleted, on the root itself

    before = prune.PRUNER.depth
    with pytest.MonkeyPatch.context() as mp:
        _run_loop(mp, fake)
    assert prune.PRUNER.depth > before, "the re-arm threw away the deletion event"


def test_the_watcher_rearms_after_an_error_instead_of_dying(repo):
    """One ENOSPC, or one root that vanishes between `_roots()` and arming, must
    not end watching until the daemon is restarted. `start()` returns early on a
    live thread and nothing else calls it, so the loop is the only restart path.
    """
    root = repo("erroring", TWO)
    registry.claim(root, direct=True)
    _drain()
    passes = []

    def fake(*roots, **_kw):
        passes.append(roots)
        if len(passes) == 1:
            raise OSError(28, "No space left on device")
        watch._stop.set()
        return iter(())

    with pytest.MonkeyPatch.context() as mp:
        _run_loop(mp, fake)
    assert len(passes) >= 2, "the loop died on the first error instead of re-arming"
