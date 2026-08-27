"""Enumeration and the content-hash diff, on real repositories."""

from __future__ import annotations

from graphrag import discover, filters


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
