"""S-06. The helper that resolves a build, and the two things it will not do.

It installs and never indexes, where `run.py` indexes and never installs. A
package manager executes code it just downloaded, so the guard here is not a
nicety — it is the reason this surface is allowed to exist at all.
"""

from __future__ import annotations

import pytest

from graphrag import index
from graphrag.scip import deps, run


def test_a_command_that_runs_lifecycle_scripts_is_refused():
    """`T-266`. The guard, and then the shipped table graded by it.

    A list of safe commands written here would agree with itself. The second
    half reads the table this module would actually run, so a plan added without
    the flag fails at collection rather than in a subprocess that has already
    fetched and executed something.
    """
    assert deps.check(("npm", "install")) != ""
    assert deps.check(("pnpm", "install")) != ""
    assert deps.check(()) != ""
    assert deps.check(("npm", "ci", "--ignore-scripts")) == ""
    # `go mod download` fetches modules and runs none of their code, so it needs
    # no suppressor and must not be refused for lacking one.
    assert deps.check(("go", "mod", "download")) == ""

    for name, rows in deps.PLANS.items():
        for marker, argv in rows:
            assert deps.check(argv) == "", (name, marker)

    # A plan for a tool no indexer row names is a command that can never run.
    assert set(deps.PLANS) <= set(run.INDEXERS)


def test_a_bad_plan_is_refused_where_it_is_chosen_and_not_where_it_was_written(
    tmp_path, monkeypatch
):
    """The table is data, and data drifts. This is what will not hand a row back."""
    (tmp_path / "package-lock.json").write_text("{}\n")
    assert deps.plan("scip-typescript", tmp_path) == ("npm", "ci", "--ignore-scripts")

    monkeypatch.setitem(deps.PLANS, "scip-typescript", (("package-lock.json", ("npm", "install")),))
    with pytest.raises(deps.RefusedError) as caught:
        deps.plan("scip-typescript", tmp_path)
    assert "--ignore-scripts" in str(caught.value)


def test_a_unit_with_no_marker_has_no_plan(tmp_path):
    """The lockfile decides the manager, so no lockfile is a refusal and not npm."""
    (tmp_path / "package.json").write_text("{}\n")
    with pytest.raises(deps.RefusedError) as caught:
        deps.plan("scip-typescript", tmp_path)
    assert str(tmp_path) in str(caught.value)

    with pytest.raises(deps.RefusedError):
        deps.plan("scip-php", tmp_path)


def test_the_helper_resolves_nothing_a_project_cannot_use(repo, monkeypatch):
    """Only `installable`. A `manual` or `absent` root buys a run that still fails.

    Asserted by running the real entry point with `subprocess.run` replaced, so
    what is graded is which commands it would have started. The index pass runs
    before the patch: `deps` holds no private reference to `subprocess`, so
    stubbing the attribute stubs it for `discover` too.
    """
    root = repo("php-only", {"Orders.php": "<?php\nclass Orders {}\n"})
    index.index_once(root)

    started = []
    monkeypatch.setattr(run.shutil, "which", lambda _name: None)
    monkeypatch.setattr(deps.subprocess, "run", lambda argv, **_kw: started.append(argv))
    assert deps.resolve(root) == []
    assert started == []
