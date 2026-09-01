"""One SQLite file per project: files, nodes, edges and an FTS5 index.

The rowid contract, stated once, here, because two tables depend on it and only
one of them enforces anything:

    nodes.id  ==  nodes_fts rowid

`nodes_fts` is an external-content table over `nodes`, and it does **not**
participate in foreign-key cascade. Deleting a row from `nodes` leaves the FTS
index holding it, and the symptom is not an error. It is `find_symbol` returning
a location that no longer exists, which reads exactly like a working engine. So
every delete touches both tables explicitly, in one transaction.

There is no ALTER path. A schema or algorithm change wipes and rebuilds, and
`incompatible()` returns *why* rather than a bare boolean, because an operator
who sees a rebuild wants to know what moved.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
  id      INTEGER PRIMARY KEY,
  path    TEXT NOT NULL UNIQUE,
  mtime   REAL NOT NULL,
  size    INTEGER NOT NULL,
  sha256  TEXT NOT NULL,
  lang    TEXT NOT NULL DEFAULT '',
  n_lines INTEGER NOT NULL DEFAULT 0,
  -- none | imports | symbols | scip. What this file actually answers, which is
  -- not what its language answers in general: a parse can fail on one file.
  tier    TEXT NOT NULL DEFAULT 'none'
);

CREATE TABLE IF NOT EXISTS nodes (
  id             INTEGER PRIMARY KEY,
  file_id        INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  kind           TEXT NOT NULL,
  name           TEXT NOT NULL,
  qualified_name TEXT NOT NULL DEFAULT '',
  start_byte     INTEGER NOT NULL,
  end_byte       INTEGER NOT NULL,
  start_line     INTEGER NOT NULL,
  end_line       INTEGER NOT NULL,
  -- The end of the enclosing scope, for attributing a call to its caller. A
  -- reference is inside the definition whose body span contains it.
  body_end_byte  INTEGER NOT NULL DEFAULT 0,
  signature      TEXT NOT NULL DEFAULT '',
  doc            TEXT NOT NULL DEFAULT '',
  tier           TEXT NOT NULL DEFAULT 'treesitter',
  -- The identifier token range, and the key SCIP ingestion upserts on. Not the
  -- enclosing range: indexers disagree on whether a decorator falls inside it.
  UNIQUE(file_id, start_byte, end_byte)
);
CREATE INDEX IF NOT EXISTS nodes_file ON nodes(file_id);
CREATE INDEX IF NOT EXISTS nodes_name ON nodes(name, kind);

CREATE TABLE IF NOT EXISTS edges (
  id              INTEGER PRIMARY KEY,
  src             INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  dst             INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  kind            TEXT NOT NULL,
  confidence      REAL NOT NULL,
  candidate_count INTEGER NOT NULL DEFAULT 1,
  -- Derived, and stored: the query surface filters on it on every call, and a
  -- computed predicate there cannot use an index.
  resolved        INTEGER NOT NULL DEFAULT 0,
  evidence        TEXT NOT NULL,
  call_site_byte  INTEGER NOT NULL DEFAULT 0,
  producer        TEXT NOT NULL DEFAULT 'treesitter'
);
CREATE INDEX IF NOT EXISTS edges_src ON edges(src, kind);
CREATE INDEX IF NOT EXISTS edges_dst ON edges(dst, kind);
CREATE INDEX IF NOT EXISTS edges_resolved ON edges(dst, kind) WHERE resolved = 1;

CREATE TABLE IF NOT EXISTS refs (
  id             INTEGER PRIMARY KEY,
  file_id        INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  kind           TEXT NOT NULL,
  name           TEXT NOT NULL,
  receiver       TEXT NOT NULL DEFAULT '',
  is_member      INTEGER NOT NULL DEFAULT 0,
  call_site_byte INTEGER NOT NULL,
  line           INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS refs_name ON refs(name, kind);
CREATE INDEX IF NOT EXISTS refs_file ON refs(file_id);

CREATE TABLE IF NOT EXISTS imports (
  id      INTEGER PRIMARY KEY,
  file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  module  TEXT NOT NULL,
  symbol  TEXT NOT NULL DEFAULT '',
  alias   TEXT NOT NULL DEFAULT '',
  line    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS imports_file ON imports(file_id);
CREATE INDEX IF NOT EXISTS imports_module ON imports(module);

CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
  name, qualified_name, signature, content='nodes', content_rowid='id',
  tokenize="unicode61 remove_diacritics 0 tokenchars '_$.'"
);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

# The edge kinds, closed. No tool takes a kind from a caller, so this set is not
# a request validator. It is the vocabulary `query.QUESTIONS` maps a question
# onto, and a question outside that map is refused naming the map.
EDGE_KINDS: frozenset[str] = frozenset(
    {"DEFINES", "CONTAINS", "IMPORTS", "CALLS", "REFERENCES", "IMPLEMENTS"}
)

# Every kind a writer produces, and nothing else. `write_nodes` produces
# `module`, `queries.DEFINITION_KINDS` produces the rest, and the SCIP overlay
# maps into the same set. `file` and `external` were declared and never written,
# and a declared-only kind is a filter a reader writes against nothing.
NODE_KINDS: frozenset[str] = frozenset(
    {"module", "class", "function", "method", "field", "constant"}
)

# What resolved an edge or a derived hop, closed. `resolve.py` and `resolvedb.py`
# produce the first five, and the overlay in `scip/ingest.py` produces `scip`.
# Three modules write this column and none of them read the others, so the set is
# graded against a real index rather than trusted.
EVIDENCE: frozenset[str] = frozenset(
    {"same_class", "same_file", "import", "package", "global", "scip"}
)


def connect(path: Path | str, *, create: bool = True) -> sqlite3.Connection:
    """Open one project's graph.

    WAL, because the query surface reads while the single writer writes. Foreign
    keys on, because the cascade from `files` is what makes a re-index of one
    file a delete plus an insert rather than a hand-written sweep.
    """
    path = Path(path)
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # First, and before `journal_mode`. `auto_vacuum` takes only on a database
    # whose header has not been written yet, and setting WAL writes it. An
    # existing store ignores this and converts only under `compact`, which needs
    # free space equal to the file and stays a human's call.
    conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    if create:
        conn.executescript(SCHEMA)
    return conn


def reclaim(conn: sqlite3.Connection) -> None:
    """Give the pages a whole-tree rewrite freed back to the filesystem.

    A whole-tree pass frees most of the old graph, and nothing returned those
    pages before this: the file only ever grew, whatever the project did. The
    per-file pass does not call this, because `wal_checkpoint(TRUNCATE)` is
    fsync-bound and that pass runs on every save. Incremental, because the full
    `VACUUM` rewrites the whole file and belongs behind a hand-typed command.
    """
    conn.execute("PRAGMA incremental_vacuum")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def compact(conn: sqlite3.Connection) -> None:
    """Rewrite the file whole. The one-time conversion for a store that predates
    `auto_vacuum`, and the only thing that reclaims its standing freelist."""
    conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
    conn.execute("VACUUM")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def get_meta(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def stamp(conn: sqlite3.Connection, *, grammars: str = "", queries: str = "") -> None:
    """Record what produced this graph, so a later open can tell it is stale."""
    set_meta(conn, "algorithm", str(config.EXTRACTION_ALGORITHM))
    set_meta(conn, "grammars", grammars)
    set_meta(conn, "queries", queries)


def incompatible(conn: sqlite3.Connection, *, grammars: str = "", queries: str = "") -> str:
    """Why this graph cannot be used, or an empty string.

    A reason and not a boolean. A rebuild that discards an hour of extraction
    has to say what moved, or the operator is left guessing at a pin bump.
    """
    stored = get_meta(conn, "algorithm")
    if not stored:
        return "the graph carries no algorithm stamp"
    if stored != str(config.EXTRACTION_ALGORITHM):
        return f"extraction algorithm moved from {stored} to {config.EXTRACTION_ALGORITHM}"
    if grammars and get_meta(conn, "grammars") != grammars:
        return "the grammar pin moved"
    if queries and get_meta(conn, "queries") != queries:
        return "a query hash moved"
    return ""


def wipe(path: Path | str) -> None:
    """Discard a graph outright, WAL sidecars included."""
    path = Path(path)
    for suffix in ("", "-wal", "-shm"):
        Path(str(path) + suffix).unlink(missing_ok=True)


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    """What the reach notice reports: nodes, edges, and how many are facts."""
    one = conn.execute(
        "SELECT (SELECT count(*) FROM files) AS files, "
        "(SELECT count(*) FROM nodes) AS nodes, "
        "(SELECT count(*) FROM edges) AS edges, "
        "(SELECT count(*) FROM edges WHERE resolved = 1) AS resolved"
    ).fetchone()
    return {k: one[k] for k in ("files", "nodes", "edges", "resolved")}
