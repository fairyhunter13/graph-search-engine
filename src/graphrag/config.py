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
EXTRACTION_ALGORITHM = 2

# -------------------------------------------------------------------- serving

LOG_LEVEL = _env("LOG_LEVEL", "INFO").upper()

HOST = _env("HOST", "127.0.0.1")
# 8766, one past coderag on 8765. The port is fixed and documented: a silent
# rebind makes a registered client point at nothing and look correct doing it.
PORT = _env_int("PORT", 8766)
MCP_URL = f"http://{HOST}:{PORT}/mcp"
HEALTHZ_URL = f"http://{HOST}:{PORT}/healthz"
# A SessionStart hook carries no MCP client roots, so it enrols over plain HTTP.
REGISTER_URL = f"http://{HOST}:{PORT}/register"

# ---------------------------------------------------------------- operations

# The two-sample rule holds the previous failing set here. Without it a checker
# compares against nothing and pages on every transient failure.
HEALTH_STATE_PATH = STATE_DIR / "health.json"

# A queue this deep that is no shallower than at the last check is not draining.
# The identity carries no count, because the rule compares identities and one
# that moves between samples pages on neither.
HEALTH_QUEUE_STUCK = _env_int("HEALTH_QUEUE_STUCK", 20)

# A ledger is evidence, and nothing reads it back as state. One generation is
# kept by rename, so a question asked after a rotation still has rows to read.
LEDGER_MAX_BYTES = _env_int("LEDGER_MAX_BYTES", 2 * 1024 * 1024)

# Progress is throttled, and a terminal write bypasses the throttle. The last
# write is the one a reader needs most.
PROGRESS_WRITE_S = float(_env("PROGRESS_WRITE_S") or "1.0")

# How long the watcher blocks before it looks at the re-arm flag. A re-arm tears
# down every watch and rebuilds it, and inotify has no replay, so everything
# inside that window is lost. Re-arming only on a changed set is what bounds it.
WATCH_POLL_MS = _env_int("WATCH_POLL_MS", 1000)
WATCH_DEBOUNCE_MS = _env_int("WATCH_DEBOUNCE_MS", 400)

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

# The project's `.graphrag.yaml` is the opt-in, and the overlay is off in every
# project that does not ask, because every indexer needs a resolved build and
# tree-sitter needs none. This switch only ever subtracts: an operator sets it
# to 0 to disable the tier on one machine without editing any project.
SCIP_ENABLED = _env_flag("SCIP_ENABLED", True)

# The coverage guard's two floors, as a share of the tree-sitter census. A SCIP
# index under either is refused rather than ingested: `scip-python` drops every
# cross-package reference on a `src/` layout and still exits 0, and a partial
# overlay is worse than none because it reads as resolved.
SCIP_FILE_COVERAGE = float(_env("SCIP_FILE_COVERAGE") or "0.60")
SCIP_DEF_COVERAGE = float(_env("SCIP_DEF_COVERAGE") or "0.40")

# ------------------------------------------------------------- the T-07 corpus

# The measurement runs against a clone pinned to a tag, fetched once. A distro
# copy of the standard library was rejected: an update moves the number, and no
# other machine reproduces it. The tag rides in the receipt, so an attester
# compares like with like.
CORPUS_REF = _env("CORPUS_REF", "v3.12.7")
CORPUS_DIR = Path(_env("CORPUS_DIR") or (Path.home() / ".cache" / APP / "corpus")).expanduser()


def corpus_root(ref: str = "") -> Path:
    """Where the pinned checkout lives. Absent means the case skips, not fails."""
    return CORPUS_DIR / f"cpython-{ref or CORPUS_REF}"


# ---------------------------------------------------------------- public gate

# Unset is the failing state, and `none` is how a clean clone declares it has
# no banned names. A guard that stands down on a missing input passes on every
# machine that never set it.
NAME_BAN = _env("NAME_BAN")
