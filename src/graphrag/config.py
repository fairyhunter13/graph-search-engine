"""Constants, paths, and the environment switches.

Nothing here imports another graphrag module: everything else depends on this,
so a cycle would be unresolvable.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

APP = "graphrag"

# ---------------------------------------------------------------- environment


def _env(name: str, default: str = "") -> str:
    return os.environ.get(f"GRAPHRAG_{name}", default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"GRAPHRAG_{name}={raw!r} is not an integer") from exc


def _env_flag(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    return raw in ("1", "true", "yes", "on") if raw else default


# ---------------------------------------------------------------------- paths

STATE_DIR = Path(_env("STATE_DIR") or (Path.home() / ".local" / "share" / APP)).expanduser()
REGISTRY_PATH = STATE_DIR / "projects.json"
REGISTRY_LOCK = STATE_DIR / "projects.lock"
BACKUP_DIR = STATE_DIR / "backups"
INDEX_DIR = STATE_DIR / "graphs"
PROGRESS_DIR = STATE_DIR / "progress"
LEDGER_DIR = STATE_DIR / "ledgers"

PROJECT_CONFIG_NAME = ".graphrag.yaml"
# One spelling, not two. `.yml` would be a second name to get right in every
# repo, and a second branch in every test that writes one. The retired name is
# refused by name rather than ignored, because a config nobody reads is worse
# than one that fails.
RETIRED_CONFIG_NAME = ".graphrag.toml"

# The registry is the only state here that cannot be re-derived from disk.
BACKUP_KEEP = 20

# A store nothing has written to for this long is not being indexed right now.
PRUNE_MIN_IDLE_S = _env_int("PRUNE_MIN_IDLE_S", 60)


def index_path(project: Path | str) -> Path:
    """Where a project's graph lives.

    Keyed by a hash of the resolved path, and never written inside the project
    itself: the engine indexes read-only trees, and a store inside a repo is a
    file the watcher would then see change.
    """
    resolved = str(Path(project).resolve())
    digest = hashlib.sha256(resolved.encode()).hexdigest()[:16]
    return INDEX_DIR / f"{Path(resolved).name}-{digest}" / "graph.db"


# ------------------------------------------------------------------ rebuilding

# The extraction algorithm number. Bump it whenever a change alters the nodes or
# the edges produced from unchanged input. `store.incompatible` compares it and
# the indexer wipes: there is no ALTER path, because a half-migrated graph
# answers a structural question with a mix of two algorithms and says nothing.
EXTRACTION_ALGORITHM = 1

# -------------------------------------------------------------------- serving

LOG_LEVEL = _env("LOG_LEVEL", "INFO").upper()

HOST = _env("HOST", "127.0.0.1")
# 8766, one past coderag on 8765. The port is fixed and documented: a silent
# rebind makes a registered client point at nothing and look correct doing it.
PORT = _env_int("PORT", 8766)
MCP_URL = f"http://{HOST}:{PORT}/mcp"

# ------------------------------------------------------------------- querying

# The confidence floor. An edge below this is dropped rather than stored: a
# repo-global match against 40 homonyms scores 0.0075, and storing it prices a
# guess as a fact in every count the query surface reports.
CONFIDENCE_FLOOR = float(_env("CONFIDENCE_FLOOR") or "0.05")

# The depth ceiling for a transitive walk. Asked for more, the tool refuses and
# names the ceiling, rather than returning a truncated answer that reads whole.
MAX_DEPTH = _env_int("MAX_DEPTH", 8)

# Discovery stops here. A member's members are not the root's members.
FEDERATION_DEPTH = _env_int("FEDERATION_DEPTH", 1)

# The SCIP overlay is opt-in per project and off everywhere by default. Every
# indexer needs a resolved build, and tree-sitter needs none.
SCIP_ENABLED = _env_flag("SCIP_ENABLED", False)

# ---------------------------------------------------------------- public gate

# Unset is the failing state, and `none` is how a clean clone declares it has
# no banned names. A guard that stands down on a missing input passes on every
# machine that never set it.
NAME_BAN = _env("NAME_BAN")
