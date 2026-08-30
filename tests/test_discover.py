"""Enumeration and the content-hash diff, on real repositories."""

from __future__ import annotations

import subprocess

from graphrag import discover, filters


def test_a_populated_submodule_is_enumerated(repo, submodule):
    """`ls-files` lists a gitlink and never descends, so this was empty."""
    root = repo(files={"app/a.py": "x = 1\n"})
    submodule(root, "Domain", {"b.py": "y = 2\n", "deep/c.py": "z = 3\n"})

    found = {m.rel_path for m in discover.enumerate_files(root)}
    assert found == {"app/a.py", "Domain/b.py", "Domain/deep/c.py"}


def test_an_exclude_still_drops_a_submodule_file(repo, submodule):
    """The path is relative to the outer root, so the outer list still bites."""
    root = repo(files={"app/a.py": "x = 1\n"})
    submodule(root, "Domain", {"b.py": "y = 2\n"})
    submodule(root, "Other", {"c.py": "z = 3\n"}, name="other")

    found = {m.rel_path for m in discover.enumerate_files(root, exclude=["Domain/*"])}
    # The kept sibling is what reds this arm on the pre-fix code, where the
    # absence of `Domain/b.py` holds for the wrong reason.
    assert found == {"app/a.py", "Other/c.py"}


def test_an_empty_submodule_directory_adds_nothing(repo, submodule):
    """47 of 69 worktrees in this workspace hold exactly this."""
    root = repo(files={"app/a.py": "x = 1\n"})
    submodule(root, "Domain", {"b.py": "y = 2\n"})
    subprocess.run(
        ["git", "submodule", "deinit", "-f", "Domain"], cwd=root, check=True, capture_output=True
    )

    assert (root / "Domain").is_dir()
    assert {m.rel_path for m in discover.enumerate_files(root)} == {"app/a.py"}


def test_a_nested_submodule_is_reached(repo, submodule):
    """The recursion, and the bound on it. `Domain` holds its own gitlink."""
    inner = repo("mid", {"b.py": "y = 2\n"})
    submodule(inner, "Shared", {"c.py": "z = 3\n"}, name="leaf")
    root = repo(files={"a.py": "x = 1\n"})
    subprocess.run(
        [
            "git",
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            "-q",
            "--",
            str(inner),
            "Domain",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-c", "protocol.file.allow=always", "submodule", "update", "--init", "--recursive"],
        cwd=root,
        check=True,
        capture_output=True,
    )

    found = {m.rel_path for m in discover.enumerate_files(root)}
    assert found == {"a.py", "Domain/b.py", "Domain/Shared/c.py"}


def test_git_ignored_files_are_never_enumerated(repo):
    root = repo(
        files={
            "src/a.py": "def a(): pass\n",
            "build/generated.py": "def g(): pass\n",
            ".gitignore": "build/\n",
        }
    )
    found = {m.rel_path for m in discover.enumerate_files(root)}
    assert found == {"src/a.py"}


def test_a_tree_that_is_not_a_repo_is_walked(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "b.py").write_text("y = 2\n")

    found = {m.rel_path for m in discover.enumerate_files(tmp_path)}
    assert found == {"pkg/a.py"}


def test_the_diff_ignores_mtime_and_reads_content(repo):
    root = repo(files={"a.py": "x = 1\n", "b.py": "y = 2\n"})
    disk = discover.enumerate_files(root)
    stored = {m.rel_path: m.sha256 for m in disk}

    (root / "a.py").touch()
    assert not discover.diff(discover.enumerate_files(root), stored)

    (root / "a.py").write_text("x = 2\n")
    (root / "c.py").write_text("z = 3\n")
    (root / "b.py").unlink()
    moved = discover.diff(discover.enumerate_files(root), stored)

    assert [m.rel_path for m in moved.changed] == ["a.py"]
    assert [m.rel_path for m in moved.added] == ["c.py"]
    assert moved.removed == ("b.py",)
    assert moved.n_touched == 3


def test_a_file_over_the_ceiling_is_not_indexable(tmp_path):
    big = tmp_path / "big.py"
    big.write_bytes(b"# " + b"x" * filters.MAX_FILE_BYTES)
    assert not filters.indexable(big)


def test_a_file_with_no_grammar_is_not_enumerated_as_source(tmp_path):
    (tmp_path / "notes.txt").write_text("hello\n")
    assert discover.enumerate_files(tmp_path) == []


def test_the_language_count_is_what_doctor_reports(repo):
    root = repo(files={"a.py": "x = 1\n", "b.py": "y = 2\n", "c.ts": "export const z = 3;\n"})
    assert discover.languages(discover.enumerate_files(root)) == {"python": 2, "typescript": 1}


def test_a_home_or_system_directory_is_refused_as_a_root(tmp_path):
    assert filters.is_forbidden_root("/")
    assert filters.is_forbidden_root("~")
    assert not filters.is_forbidden_root(tmp_path)
