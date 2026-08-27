"""One index pass, and the queue that serializes them.

The queue is the write serializer. There is no second write lock, because a
lock plus a queue is two answers to one question and they drift apart.

Its dedup is asymmetric on purpose. A job already queued is dropped, because
the queued pass has not read the tree yet and will see the change. A job whose
root is already *running* is queued again, because the running pass may have
read the tree before the change landed. Losing that re-queue is a missed edit
that never heals until the next full pass.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from . import (
    config,
    discover,
    extract,
    grammars,
    indexwrite,
    ledger,
    progress,
    registry,
    resolve,
    store,
    symtab,
    trace,
)

log = logging.getLogger(__name__)


@dataclass(slots=True)
class IndexReport:
    """What one pass did. `rebuilt` names why a graph was discarded."""

    root: str
    files: int = 0
    nodes: int = 0
    edges: int = 0
    resolved: int = 0
    parsed: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    rebuilt: str = ""
    unchanged: bool = False
    errors: dict[str, str] = field(default_factory=dict)


def _facts(root: Path, metas: list[discover.FileMeta]) -> dict[str, extract.FileFacts]:
    """Parse every indexable file. Resolution is global, so a partial parse
    would price every unparsed file as a repo that does not define the name."""
    out: dict[str, extract.FileFacts] = {}
    parsable = [meta for meta in metas if meta.lang]
    progress.begin(root, len(parsable))
    for meta in parsable:
        try:
            text = (root / meta.rel_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            out[meta.rel_path] = extract.FileFacts(lang=meta.lang, error=str(exc))
            progress.advance()
            continue
        out[meta.rel_path] = extract.extract(meta.lang, text)
        progress.advance()
    return out


def index_once(root: Path | str, *, force: bool = False) -> IndexReport:
    """Enumerate, diff, parse, resolve and write. The whole engine in one call."""
    root = Path(root).resolve()
    report = IndexReport(root=str(root))
    path = config.index_path(root)

    conn = store.connect(path)
    reason = store.incompatible(conn)
    if reason:
        conn.close()
        store.wipe(path)
        conn = store.connect(path)
        report.rebuilt = reason

    metas = discover.enumerate_files(root)
    report.languages = discover.languages(metas)
    stored = {
        row["path"]: row["sha256"]
        for row in conn.execute(
            "SELECT path, sha256 FROM files WHERE path != ?", (indexwrite.EXTERNAL_PATH,)
        )
    }
    changes = discover.diff(metas, stored)
    if not changes and not force and not report.rebuilt:
        conn.close()
        report.unchanged = True
        report.files = len(metas)
        return report

    facts = _facts(root, metas)
    report.parsed = len(facts)
    report.errors = {p: f.error for p, f in facts.items() if f.error}
    table = symtab.build({p: f for p, f in facts.items() if not f.error})

    with conn:
        conn.execute("DELETE FROM files")
        file_ids = indexwrite.write_files(conn, metas, facts)
        nodes = indexwrite.write_nodes(conn, table, file_ids)

        progress.phase("resolving")
        resolutions = {p: resolve.resolve_file(table, p) for p in table.files}
        external = {r.reference.name for rows in resolutions.values() for r in rows if r.external}
        externals = indexwrite.write_externals(conn, external)

        edges = indexwrite.structural_edges(table, nodes) + indexwrite.import_edges(table, nodes)
        for p, rows in resolutions.items():
            edges += indexwrite.reference_edges(p, rows, nodes, externals)
        indexwrite.write_edges(conn, edges)
        indexwrite.rebuild_fts(conn)
        store.stamp(conn)

    totals = store.counts(conn)
    conn.close()
    report.files = totals["files"]
    report.nodes = totals["nodes"]
    report.edges = totals["edges"]
    report.resolved = totals["resolved"]
    progress.finish()
    return report


def record(report: IndexReport) -> None:
    """Write the pass into the registry row, counts included.

    The reach hook reads the row and not the store, so a row with no figures
    reports an indexed project as an empty one."""
    counts = None
    caps = None
    if not report.unchanged:
        counts = (report.nodes, report.edges, report.resolved)
        caps = {lang: sorted(grammars.capabilities(lang)) for lang in report.languages}
    registry.mark_indexed(report.root, counts=counts, capabilities=caps)


class Queue:
    """One queue, one worker. The queue is the state, and it is asymmetric."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._waiting: deque[str] = deque()
        self._queued: set[str] = set()
        self._running: set[str] = set()
        self._wake = threading.Condition(self._lock)

    def submit(self, root: Path | str) -> str:
        """Returns `queued`, `dropped` or `requeued`, and the third is the point."""
        key = str(Path(root).resolve())
        with self._wake:
            if key in self._queued:
                return "dropped"
            verdict = "requeued" if key in self._running else "queued"
            self._queued.add(key)
            self._waiting.append(key)
            self._wake.notify()
            return verdict

    def take(self, timeout: float = 1.0) -> str | None:
        with self._wake:
            if not self._waiting and not self._wake.wait(timeout):
                return None
            if not self._waiting:
                return None
            key = self._waiting.popleft()
            self._queued.discard(key)
            self._running.add(key)
            return key

    def done(self, key: str) -> None:
        with self._wake:
            self._running.discard(key)

    @property
    def depth(self) -> int:
        with self._lock:
            return len(self._waiting)


QUEUE = Queue()


def run_worker(queue: Queue = QUEUE, *, stop: threading.Event | None = None) -> None:
    """Drain the queue until told to stop. One thread, so one writer."""
    stop = stop or threading.Event()
    while not stop.is_set():
        key = queue.take()
        if key is None:
            continue
        with trace.span():
            try:
                report = index_once(key)
                record(report)
                ledger.append(
                    ledger.RUN,
                    {
                        "kind": "index",
                        "root": key,
                        "files": report.files,
                        "parsed": report.parsed,
                        "edges": report.edges,
                        "resolved": report.resolved,
                        "unchanged": report.unchanged,
                        "rebuilt": report.rebuilt,
                    },
                )
            except Exception as exc:
                # The row carries the failure, so the health rule can hold it
                # across two samples. A worker that dies on one project stops
                # indexing every other one.
                registry.mark_indexed(key, error=str(exc))
                ledger.append(ledger.RUN, {"kind": "index", "root": key, "error": str(exc)})
                log.exception("index pass failed for %s", key)
            finally:
                queue.done(key)
