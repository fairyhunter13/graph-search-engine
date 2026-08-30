"""Members found by walking symlinks, and the two lists a project excludes.

Real directories and real symlinks. A symlink cycle and a broken link are the
two cases a walk meets in this workspace within a day, so both are here.
"""

from __future__ import annotations

import pytest

from graphrag import discover, federation, index, registry, tools

SRC = {"a.py": "def alpha():\n    return 1\n"}


@pytest.fixture
def tree(repo):
    """A root reaching three projects by link, one of them under `worktrees/`."""
    one = repo("one", SRC)
    two = repo("two", SRC)
    # The second checkout of a repo, where this workspace really keeps them.
    # The link name says nothing about that, and the target says everything.
    hidden = repo("_worktrees/two/release", SRC)
    root = repo("root", SRC)
    links = root / "repositories"
    links.mkdir()
    (links / "one").symlink_to(one)
    (links / "two").symlink_to(two)
    (links / "two-release").symlink_to(hidden)
    return root, one, two, hidden


def test_a_symlink_enrols_the_project_it_points_at(tree):
    """The whole ruling, in one assertion: no member is declared anywhere."""
    root, one, two, hidden = tree
    assert federation.members_of(root) == sorted([one, two, hidden])


def test_the_resolved_target_is_the_key_and_never_the_link(tree):
    """inotify does not traverse a symlink, so a link as a key watches nothing."""
    root, one, _two, _hidden = tree
    federation.register(root)
    keys = set(registry.load())
    assert str(one) in keys
    assert str(root / "repositories" / "one") not in keys


def test_two_links_to_one_target_are_one_member(tree):
    """Deduplicated by resolved target. This tree reaches a repo many ways."""
    root, one, two, hidden = tree
    (root / "repositories" / "one-again").symlink_to(one)
    assert federation.members_of(root) == sorted([one, two, hidden])


def test_a_broken_link_is_skipped_and_never_registered(tree):
    """`strict=True`, so a dangling link is not a member with a missing path."""
    root, one, two, hidden = tree
    (root / "repositories" / "gone").symlink_to(root.parent / "no-such-repo")
    assert federation.members_of(root) == sorted([one, two, hidden])


def test_a_symlink_cycle_terminates(tree):
    """A link pointing at its own root is dropped, not walked."""
    root, one, two, hidden = tree
    (root / "repositories" / "self").symlink_to(root)
    assert federation.members_of(root) == sorted([one, two, hidden])


def test_federation_exclude_matches_the_target_and_not_only_the_link(tree):
    """The pattern names the target layout, which is the only place it appears.

    A pattern matched against the link alone re-admits every second checkout of
    a repo the root already reaches under its own name.
    """
    root, one, two, hidden = tree
    # The link is `repositories/two-release`, which the pattern does not match.
    # Only the target carries `_worktrees`, so this arm fails against a check
    # that reads the link alone.
    assert "_worktrees" not in str(root / "repositories" / "two-release")
    (root / ".graphrag.yaml").write_text("federation_exclude: ['*/_worktrees/*']\n")
    assert hidden not in federation.members_of(root)
    assert federation.members_of(root) == sorted([one, two])


def test_a_declared_member_survives_the_walk(tree, repo):
    """`members:` adds. A project no symlink reaches can still be named."""
    root, one, two, hidden = tree
    named = repo("named", SRC)
    (root / ".graphrag.yaml").write_text(f"members: ['{named}']\n")
    assert federation.members_of(root) == sorted([one, two, hidden, named])


def test_exclude_removes_a_directory_from_the_index_pass(repo):
    """`T-4.3`: the key was parsed and read by nothing until 2026-08-30.

    The negative arm is the second assertion. Against the old code both counts
    are 2, because `enumerate_files` took no exclude at all.
    """
    root = repo(
        "excluded",
        {
            "app/main.py": "def main():\n    return 1\n",
            "system/core/CodeIgniter.py": "def boot():\n    return 2\n",
        },
    )
    assert len(discover.enumerate_files(root)) == 2
    kept = discover.enumerate_files(root, exclude=["system/*"])
    assert [m.rel_path for m in kept] == ["app/main.py"]


def test_exclude_reaches_the_index_through_the_project_config(repo):
    """Wired end to end, because a key read only by a test is still unwired."""
    root = repo(
        "wired",
        {
            "app/main.py": "def main():\n    return 1\n",
            "system/core/CodeIgniter.py": "def boot():\n    return 2\n",
        },
    )
    # The config counts as a file of its own, so it excludes itself too.
    (root / ".graphrag.yaml").write_text("exclude: ['system/*', '*.yaml']\n")
    report = index.index_once(root)
    assert report.files == 1
    assert report.languages == {"python": 1}


def test_languages_keeps_only_what_the_project_names(repo):
    """The other accepted-and-ignored key. Wired, rather than deleted."""
    root = repo(
        "langs",
        {"a.py": "def alpha():\n    return 1\n", "b.sh": "alpha() { echo 1; }\n"},
    )
    (root / ".graphrag.yaml").write_text("languages: ['python']\n")
    metas = discover.enumerate_files(root, languages=["python"])
    assert [m.rel_path for m in metas] == ["a.py"]
    assert index.index_once(root).languages == {"python": 1}


def test_a_walked_tree_honours_exclude_without_git(tmp_path):
    """The fallback branch. `_git_files` returns None outside a repository."""
    root = tmp_path / "plain"
    (root / "app").mkdir(parents=True)
    (root / "system").mkdir()
    (root / "app" / "main.py").write_text("def main():\n    return 1\n")
    (root / "system" / "boot.py").write_text("def boot():\n    return 2\n")
    assert not (root / ".git").exists()
    metas = discover.enumerate_files(root, exclude=["system/*"])
    assert [m.rel_path for m in metas] == ["app/main.py"]


def test_a_member_inherits_the_exclude_of_the_root_that_claims_it(repo):
    """A member is somebody else's repo, so no config can be written into it.

    The negative arm is the file count. Against a member that inherits nothing
    both files are indexed, and the framework directory reaches the graph.
    """
    member = repo(
        "vendored",
        {
            "app/main.py": "def main():\n    return 1\n",
            "system/core/CodeIgniter.py": "def boot():\n    return 2\n",
        },
    )
    root = repo("workspace", SRC)
    (root / "repositories").mkdir()
    (root / "repositories" / "vendored").symlink_to(member)
    (root / ".graphrag.yaml").write_text("exclude: ['system/*']\n")
    federation.register(root)

    assert not (member / ".graphrag.yaml").exists()
    report = index.index_once(member)
    assert report.files == 1
    assert report.languages == {"python": 1}


def test_a_member_with_its_own_config_inherits_nothing(repo):
    """A file somebody wrote is obeyed whole. Nothing is merged into it."""
    member = repo(
        "opinionated",
        {
            "app/main.py": "def main():\n    return 1\n",
            "system/core/CodeIgniter.py": "def boot():\n    return 2\n",
        },
    )
    root = repo("owner-of", SRC)
    (root / "repositories").mkdir()
    (root / "repositories" / "opinionated").symlink_to(member)
    (root / ".graphrag.yaml").write_text("exclude: ['system/*']\n")
    federation.register(root)

    (member / ".graphrag.yaml").write_text("exclude: ['*.yaml']\n")
    assert index.index_once(member).files == 2


def test_find_symbol_spans_the_federation_and_names_the_project(tree):
    """`T-4.8`: the caller knows the workspace, never which of 360 repos."""
    root, one, _two, _hidden = tree
    (one / "only_here.py").write_text("def only_here():\n    return 1\n")
    for project in federation.expand(root):
        index.index_once(project)

    answer = tools.find_symbol(name="only_here", root=str(root))
    assert answer["results"]
    assert {hit["project"] for hit in answer["results"]} == {str(one)}
    assert answer["searched"] == len(federation.expand(root))

    # The negative arm. Single-store is what the tool did until 2026-08-30.
    alone = tools.find_symbol(name="only_here", root=str(root), federated=False)
    assert alone["results"] == []
    assert alone["gaps"] == ["no symbol named 'only_here' is indexed in this project"]


def test_an_unindexed_member_is_a_gap_and_not_an_absence(tree):
    """A member nobody has passed answers nothing, which is not answering no."""
    root, _one, _two, _hidden = tree
    index.index_once(root)
    answer = tools.find_symbol(name="alpha", root=str(root))
    assert any("no graph yet" in gap for gap in answer["gaps"])
