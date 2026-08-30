"""Real fixtures. No mocks, and no parser stubs.

Every test gets its own state directory. The module-level path constants in
`config` are read at import, so the fixture rebinds them rather than setting the
environment after the fact.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from graphrag import config


@pytest.fixture(autouse=True)
def state_dir(tmp_path, monkeypatch):
    """Point every path constant at a directory this test alone owns."""
    root = tmp_path / "state"
    monkeypatch.setattr(config, "STATE_DIR", root)
    monkeypatch.setattr(config, "REGISTRY_PATH", root / "projects.json")
    monkeypatch.setattr(config, "REGISTRY_LOCK", root / "projects.lock")
    monkeypatch.setattr(config, "BACKUP_DIR", root / "backups")
    monkeypatch.setattr(config, "INDEX_DIR", root / "graphs")
    monkeypatch.setattr(config, "PROGRESS_DIR", root / "progress")
    monkeypatch.setattr(config, "LEDGER_DIR", root / "ledgers")
    monkeypatch.setattr(config, "HEALTH_STATE_PATH", root / "health.json")
    return root


@pytest.fixture
def repo(tmp_path):
    """A real git repository, because `discover` asks git before it walks."""

    def make(name: str = "repo", files: dict[str, str] | None = None) -> Path:
        root = tmp_path / name
        root.mkdir(parents=True, exist_ok=True)
        for rel, text in (files or {}).items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "seed"],
            cwd=root,
            check=True,
        )
        return root

    return make


@pytest.fixture
def submodule(repo):
    """A real, populated submodule, added and committed as a gitlink."""

    def add(outer: Path, at: str, files: dict[str, str], name: str = "inner") -> Path:
        inner = repo(name, files)
        subprocess.run(
            # `protocol.file.allow` is denied by default since CVE-2022-39253,
            # and a local path is the only clone source a test has.
            ["git", "-c", "protocol.file.allow=always", "submodule", "add", "-q",
             "--", str(inner), at],
            cwd=outer,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "sub"],
            cwd=outer,
            check=True,
        )
        return outer / at

    return add
