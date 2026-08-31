"""T-02, and the two rules that removal obeys."""

from __future__ import annotations

import json
import multiprocessing as mp
import time

import pytest

from graphrag import config, quarantine, registry


def _claim_in_child(state: str, path: str) -> None:
    """A second process, so the flock is real rather than re-entrant."""
    root = __import__("pathlib").Path(state)
    config.STATE_DIR = root
    config.REGISTRY_PATH = root / "projects.json"
    config.REGISTRY_LOCK = root / "projects.lock"
    config.BACKUP_DIR = root / "backups"
    registry.claim(path, direct=True)


def test_mutate_loads_inside_the_lock(state_dir, tmp_path):
    """T-02. A writer that reads before it locks drops the other writer's row.

    The parent holds the lock and sleeps with its own row pending. The child
    blocks on the flock, and reads only after the parent has written. Both rows
    survive. A load outside the lock would leave the child holding a snapshot
    taken before the parent's write, and the parent's row would be gone.
    """
    first, second = tmp_path / "first", tmp_path / "second"
    for project in (first, second):
        project.mkdir()

    ctx = mp.get_context("fork")
    child = ctx.Process(target=_claim_in_child, args=(str(state_dir), str(second)))
    with registry._mutate() as rows:
        child.start()
        # Long enough for the child to reach the flock and block on it.
        time.sleep(0.5)
        rows[str(registry.resolve(first))] = registry.ProjectEntry(
            path=str(registry.resolve(first)), direct=True
        )
    child.join(timeout=10)
    assert child.exitcode == 0

    assert set(registry.load()) == {
        str(registry.resolve(first)),
        str(registry.resolve(second)),
    }


def test_nothing_prunes_a_row_because_its_path_is_missing(tmp_path):
    """An unmounted volume and a deleted project look identical from here."""
    gone = tmp_path / "gone"
    gone.mkdir()
    registry.claim(gone, direct=True)
    key = str(registry.resolve(gone))
    gone.rmdir()

    assert key in registry.load(), "a missing path is not a removal"

    dropped, _ = registry.forget([key])
    assert dropped == [key]
    assert key not in registry.load()


def test_forget_writes_one_backup_holding_every_row_it_removed(tmp_path):
    """`_rotate_backup` stamps to the second, so a loop overwrites its own
    backup inside that second, and what survives is a half-pruned registry."""
    keys = []
    for name in ("a", "b", "c"):
        (tmp_path / name).mkdir()
        registry.claim(tmp_path / name, direct=True)
        keys.append(str(registry.resolve(tmp_path / name)))

    registry.forget(keys)

    newest = max(config.BACKUP_DIR.glob("projects.*.json"))
    assert set(json.loads(newest.read_text())) == set(keys)
    assert registry.load() == {}


def test_forget_releases_a_member_no_surviving_root_claims(tmp_path):
    """A member claimed only by the forgotten root goes with it. One claimed
    directly stays, with the dead root gone from its `roots`: a stale root
    narrows the member's corpus through the excludes it inherits."""
    for name in ("root", "member", "shared"):
        (tmp_path / name).mkdir()
    root, member, shared = (tmp_path / n for n in ("root", "member", "shared"))
    registry.claim(root, direct=True)
    registry.claim(member, root=root)
    registry.claim(shared, direct=True, root=root)

    dropped, released = registry.forget([str(root)])

    assert dropped == [str(registry.resolve(root))]
    assert released == [str(registry.resolve(member))]
    assert registry.load()[str(registry.resolve(shared))].roots == []


def test_prune_removes_the_directory_so_the_count_reaches_zero(tmp_path):
    """`wipe` unlinks the graph but leaves the directory, and a directory is
    what `unclaimed_stores` counts. A prune that only wiped listed the same
    orphan on every run. `prune_unclaimed` rmtrees, and leaves a claimed store."""
    live = tmp_path / "live"
    live.mkdir()
    registry.claim(live, direct=True)
    kept = config.index_path(live).parent
    kept.mkdir(parents=True)
    (kept / "graph.db").write_bytes(b"claimed")

    orphan = config.INDEX_DIR / "svc-deadbeef"
    orphan.mkdir(parents=True)
    (orphan / "graph.db").write_bytes(b"orphan")

    assert registry.unclaimed_stores() == [orphan]

    assert registry.prune_unclaimed() == [orphan]

    assert not orphan.exists()
    assert kept.exists()
    assert registry.unclaimed_stores() == []


def test_quarantine_is_not_counted_as_an_orphan(tmp_path):
    """`.trash` lives under `INDEX_DIR` and no row names it. Counted, the reaper
    would delete its own undo on the next pass and report it as reclaimed."""
    live = tmp_path / "live"
    live.mkdir()
    registry.claim(live, direct=True)
    trash = quarantine.trash_dir() / "1700000000-svc-deadbeef"
    trash.mkdir(parents=True)
    (trash / "graph.db").write_bytes(b"undo")

    assert registry.unclaimed_stores() == []
    assert registry.prune_unclaimed() == []
    assert trash.is_dir(), "the reaper deleted the quarantine it had just written"


def test_a_prune_against_an_empty_registry_refuses():
    """Ported after both of the semantic engine's fleet wipes returned a verdict
    shaped like this one. A registry that failed to load reads as a fleet with
    nothing enrolled, and `--force` deliberately does not lift this."""
    orphan = config.INDEX_DIR / "svc-deadbeef"
    orphan.mkdir(parents=True)

    with pytest.raises(RuntimeError, match="empty registry"):
        registry.prune_unclaimed()
    with pytest.raises(RuntimeError, match="empty registry"):
        registry.prune_unclaimed(force=True)
    assert orphan.is_dir()


def test_a_prune_over_half_the_tree_needs_force(tmp_path):
    """A majority verdict is the shape a wipe has. It is allowed, once a human
    has said so on the command line."""
    live = tmp_path / "live"
    live.mkdir()
    registry.claim(live, direct=True)
    config.index_path(live).parent.mkdir(parents=True)
    for name in ("a-1111", "b-2222"):
        (config.INDEX_DIR / name).mkdir()

    with pytest.raises(RuntimeError, match="without --force"):
        registry.prune_unclaimed()
    assert len(registry.prune_unclaimed(force=True)) == 2


def test_a_symlinked_path_claims_the_row_it_points_at(tmp_path):
    """Resolving before ownership is decided. A path that skips it claims a
    second row, and every later answer files under the wrong root."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)

    registry.claim(real, direct=True)
    registry.claim(link, direct=True)

    assert list(registry.load()) == [str(real.resolve())]


def test_the_digest_moves_when_a_root_is_dropped_and_the_count_does_not(tmp_path):
    """A count is blind to a dead root left in a live project's `roots`."""
    for name in ("root", "member"):
        (tmp_path / name).mkdir()
    root, member = tmp_path / "root", tmp_path / "member"
    registry.claim(root, direct=True)
    registry.claim(member, direct=True, root=root)

    before = registry.fleet_digest(registry.load())
    registry.release(member, root)
    after = registry.load()

    assert len(after) == 2
    assert registry.fleet_digest(after) != before
