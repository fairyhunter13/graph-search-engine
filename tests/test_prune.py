"""Automatic removal, and the four ways it must refuse.

Every arm here is a real directory removed from a real filesystem, against a
real registry file. The clock is the one injected thing, because a test must not
spend the grace period.

The rule this replaces refused to prune at all, so each refusal arm below is the
one that keeps the replacement honest.
"""

from __future__ import annotations

import argparse
import os
import shutil
import time
from dataclasses import replace
from pathlib import Path

import pytest

from graphrag import cli, config, federation, progress, prune, quarantine, registry

SRC = {"a.py": "def alpha():\n    return 1\n"}


class Clock:
    """A hand-wound monotonic clock. `advance` is the whole grace period."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def pruner(clock):
    return prune.Pruner(grace=30.0, clock=clock)


def test_a_deleted_project_loses_its_row(repo, pruner, clock):
    """The ruling: missing or dead is removed, with no command run."""
    project = repo("gone", SRC)
    registry.claim(project, direct=True)
    shutil.rmtree(project)

    pruner.note_gone(project)
    assert pruner.run_due() == {"forgotten": [], "unclaimed": [], "quarantined": []}
    assert registry.get(project) is not None

    clock.advance(31.0)
    assert pruner.run_due()["forgotten"] == [str(project)]
    assert registry.get(project) is None


def test_a_removed_parent_keeps_the_row(repo, pruner, clock):
    """The unmount case, and the reason the old rule refused every prune.

    A repo deleted leaves its parent standing. A volume that goes away takes the
    parent with it, and the two are told apart by exactly this test.
    """
    parent = repo("volume/inner", SRC)
    registry.claim(parent, direct=True)
    shutil.rmtree(parent.parent)

    pruner.note_gone(parent)
    clock.advance(31.0)
    assert pruner.run_due()["forgotten"] == []
    assert registry.get(parent) is not None


def test_a_project_restored_inside_the_grace_period_keeps_the_row(repo, pruner, clock):
    """A checkout into a moved-aside path settles well inside the window."""
    project = repo("blinking", SRC)
    registry.claim(project, direct=True)
    shutil.rmtree(project)

    pruner.note_gone(project)
    clock.advance(10.0)
    project.mkdir()
    (project / "a.py").write_text(SRC["a.py"])

    clock.advance(21.0)
    assert pruner.run_due()["forgotten"] == []
    assert registry.get(project) is not None


def test_a_removed_link_releases_the_claim_and_the_target_survives(repo, pruner, clock):
    """The second path. No event ever fires on the target, which still exists."""
    member = repo("member", SRC)
    root = repo("root", SRC)
    links = root / "repositories"
    links.mkdir()
    (links / "member").symlink_to(member)

    federation.register(root)
    assert registry.get(member) is not None
    (links / "member").unlink()

    pruner.note_unlinked(root)
    clock.advance(31.0)
    verdict = pruner.run_due()
    assert verdict["unclaimed"] == [str(member)]
    assert verdict["forgotten"] == [str(member)]
    assert registry.get(member) is None
    # The link went. The project did not, and nothing here removed it.
    assert member.is_dir()


def test_a_removed_link_keeps_a_row_another_root_claims(repo, pruner, clock):
    """`release` drops one claim. It is not the prune that emptied a fleet."""
    member = repo("shared", SRC)
    first = repo("first", SRC)
    second = repo("second", SRC)
    for root in (first, second):
        (root / "repositories").mkdir()
        (root / "repositories" / "shared").symlink_to(member)
        federation.register(root)

    entry = registry.get(member)
    assert entry is not None
    assert sorted(entry.roots) == sorted([str(first), str(second)])

    (first / "repositories" / "shared").unlink()
    pruner.note_unlinked(first)
    clock.advance(31.0)
    verdict = pruner.run_due()
    assert verdict["unclaimed"] == [str(member)]
    assert verdict["forgotten"] == []

    entry = registry.get(member)
    assert entry is not None
    assert entry.roots == [str(second)]


def test_a_directly_enrolled_member_survives_its_link(repo, pruner, clock):
    """Enrolled on its own account, so no root's claim can remove it."""
    member = repo("own", SRC)
    root = repo("owner", SRC)
    (root / "repositories").mkdir()
    (root / "repositories" / "own").symlink_to(member)
    federation.register(root)
    registry.claim(member, direct=True)

    (root / "repositories" / "own").unlink()
    pruner.note_unlinked(root)
    clock.advance(31.0)
    pruner.run_due()
    assert registry.get(member) is not None


def test_nothing_due_reads_no_registry(pruner):
    """Called on every watcher tick, so the empty case must cost nothing."""
    assert pruner.depth == 0
    assert pruner.run_due() == {"forgotten": [], "unclaimed": [], "quarantined": []}


def _plant_store(project, *, age: float = 0.0):
    """A graph on disk for `project`, optionally aged past the idle floor."""
    store = config.index_path(project)
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_bytes(b"graph")
    if age:
        stamp = time.time() - age
        os.utime(store, (stamp, stamp))
    return store


def test_a_dead_row_takes_its_graph_with_it(repo, pruner, clock):
    """The whole leak: the row left and the bytes stayed until a human typed a
    command. Quarantined rather than deleted, so the week of undo holds."""
    project = repo("reclaimed", SRC)
    registry.claim(project, direct=True)
    store = _plant_store(project, age=config.PRUNE_MIN_IDLE_S + 1)
    shutil.rmtree(project)

    pruner.note_gone(project)
    clock.advance(31.0)
    assert pruner.run_due()["quarantined"] == [str(project)]
    assert not store.parent.exists(), "the graph outlived the row"
    trashed = list(quarantine.trash_dir().iterdir())
    assert len(trashed) == 1 and (trashed[0] / "graph.db").is_file()


def test_a_graph_written_inside_the_idle_floor_is_left_alone(repo, pruner, clock):
    """`PRUNE_MIN_IDLE_S` had no consumer at all before this. The semantic engine
    has the defect recorded: a prune raced a store the daemon was mid-write on."""
    project = repo("busy", SRC)
    registry.claim(project, direct=True)
    store = _plant_store(project)  # written just now
    shutil.rmtree(project)

    pruner.note_gone(project)
    clock.advance(31.0)
    done = pruner.run_due()
    assert done["forgotten"] == [str(project)]
    assert done["quarantined"] == []
    assert store.is_file(), "a graph written this second was taken anyway"


def test_quarantine_expires_on_its_own_clock(repo):
    """Seven days, and a name this did not write is never guessed at."""
    project = repo("expiring", SRC)
    store = _plant_store(project)
    moved = quarantine.take(store.parent)
    assert moved is not None
    stranger = quarantine.trash_dir() / "not-a-stamp"
    stranger.mkdir()

    assert quarantine.expire() == []
    gone = quarantine.expire(now=time.time() + (config.QUARANTINE_DAYS + 1) * 86400)
    assert gone == [moved]
    assert stranger.is_dir(), "a directory this did not name was deleted anyway"


def test_a_failed_quarantine_never_degrades_to_a_delete(repo, monkeypatch):
    """The one rule the first version of this carried: a rename that fails leaves
    the store standing. A path whose purpose is undo cannot delete harder."""
    project = repo("stuck", SRC)
    store = _plant_store(project)

    def refuse(_self, _target):
        raise OSError("cross-device link")

    monkeypatch.setattr(Path, "rename", refuse)
    assert quarantine.take(store.parent) is None
    assert store.is_file(), "a failed move deleted the store"


def test_an_unmounted_volume_is_never_read_as_a_deletion(repo, monkeypatch):
    """The distinction `registry.py` refuses to prune by predicate without. A
    mount point left standing after its volume goes is shaped exactly like a
    deleted repo -- the recorded device is the only thing that separates them."""
    project = repo("onvolume", SRC)
    registry.claim(project, direct=True)
    entry = registry.get(project)
    assert entry is not None and entry.dev, "the claim recorded no device"
    shutil.rmtree(project)

    assert prune.verdict(entry) == "deleted"
    # The same path, with a different filesystem answering its parent today.
    moved = replace(entry, dev=entry.dev + 1)
    assert prune.verdict(moved) == "unmounted"
    # And a row written before the device was ever recorded.
    assert prune.verdict(replace(entry, dev=0)) == "unknown"

    survey = prune.survey()
    assert survey["deleted"] == [str(project)]
    assert survey["unmounted"] == [] and survey["unknown"] == []
    # The population, not a total of the three lists: an empty `deleted` and a
    # registry that read nothing are otherwise the same answer.
    assert survey["read"] == len(registry.load())


def _plant(project: Path) -> Path:
    """A store directory and the progress file keyed to it, as an index leaves them."""
    store = config.index_path(project)
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_bytes(b"x" * 64)
    return store.parent


def test_a_progress_file_outlives_its_store_and_the_prune_sweeps_it(repo):
    """The third thing a forgotten project leaves behind, after the row and the graph.

    `progress/*.json` is keyed by store directory and written by the indexer, so
    neither `forget` nor `prune_unclaimed` reaches one. 378 of them stood on this
    fleet. The reconciliation is against the store *directory*, never the registry:
    an orphan whose store is still standing is left alone, which keeps this off the
    filesystem predicate the registry refuses.
    """
    live = repo("kept", SRC)
    dead = repo("gone", SRC)
    registry.claim(live, direct=True)
    _plant(live)
    config.PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    kept_json = progress.path_for(live)
    orphan_json = progress.path_for(dead)
    for path in (kept_json, orphan_json):
        path.write_text('{"phase": "parsing"}')

    assert cli._orphan_progress() == [orphan_json]

    assert cli.cmd_prune(argparse.Namespace(apply=False, force=False)) == 0
    assert orphan_json.is_file(), "the dry run deleted a file"

    assert cli.cmd_prune(argparse.Namespace(apply=True, force=False)) == 0

    assert not orphan_json.exists()
    assert kept_json.is_file(), "a progress file whose store still stands was swept"
