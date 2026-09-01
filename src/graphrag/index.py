"""One index pass: enumerate, diff, parse, resolve and write.

The pass rewrites the files the diff names and no others. `jobs.py` holds the
queue that serializes one pass against the next.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from . import (
    config,
    discover,
    extract,
    grammars,
    indexwrite,
    progress,
    projcfg,
    registry,
    resolve,
    store,
    symtab,
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
    # One line per SCIP indexer asked for, refusal included. Empty means the
    # overlay was not asked for, which is the default.
    scip: dict[str, str] = field(default_factory=dict)
    unchanged: bool = False
    # Whether the pass read a named path set rather than the tree. A hinted
    # pass saw part of the tree, so its `languages` is a part too.
    hinted: bool = False
    errors: dict[str, str] = field(default_factory=dict)


def _facts(root: Path, metas: list[discover.FileMeta]) -> dict[str, extract.FileFacts]:
    """Parse the files given, and only those.

    A partial parse used to be wrong, because resolution read every definition at
    once and an unparsed file priced as a repo that does not define the name.
    Resolution is file-local now, so the set handed in is the set that is
    rewritten, and a file nobody touched keeps the rows it already has.
    """
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


def _overlay(conn, root: Path, cfg: projcfg.ProjectConfig) -> dict[str, str]:
    """The SCIP tier, off unless the project asks for it and names a tool.

    Imported here and not at module scope, so a project that never enables the
    overlay never loads it. The tier is deletable in one move, and an
    unconditional import is what would quietly stop that being true.
    """
    from . import scip

    if not scip.enabled(cfg.scip) or not cfg.scip_indexers:
        return {}
    return scip.overlay(conn, root, cfg.scip_indexers)


def index_once(
    root: Path | str, *, force: bool = False, paths: frozenset[str] | None = None
) -> IndexReport:
    """Enumerate, diff, parse, resolve and write. The whole engine in one call.

    `paths` is the watcher's hint: the relative paths a batch of events named.
    Given it, the pass stats and hashes only those paths and diffs them against
    their own stored rows. Given nothing, it hashes the tree. The hint buys
    latency and the scan buys correctness, so the hint never replaces the scan.
    """
    root = Path(root).resolve()
    cfg = projcfg.effective(root)
    report = IndexReport(root=str(root))
    path = config.index_path(root)

    conn = store.connect(path)
    reason = store.incompatible(conn)
    if reason:
        conn.close()
        store.wipe(path)
        conn = store.connect(path)
        report.rebuilt = reason

    # A wiped store holds no row for the hint to diff against, and `force` asks
    # for the tree by name. Either one outranks a hint.
    if force or report.rebuilt:
        paths = None
    report.hinted = paths is not None

    rows = conn.execute("SELECT path, sha256 FROM files")
    if paths is None:
        metas = discover.enumerate_files(root, exclude=cfg.exclude, languages=cfg.languages)
        stored = {row["path"]: row["sha256"] for row in rows}
    else:
        metas = discover.enumerate_paths(root, paths, exclude=cfg.exclude, languages=cfg.languages)
        # Narrowed to the hinted names, so a file the hint does not name is not
        # read as removed and deleted.
        stored = {row["path"]: row["sha256"] for row in rows if row["path"] in paths}
    report.languages = discover.languages(metas)
    changes = discover.diff(metas, stored)
    if not changes and not force and not report.rebuilt:
        report.unchanged = True
        report.files = store.counts(conn)["files"] if report.hinted else len(metas)
        conn.close()
        return report

    # A whole-tree rewrite where the graph is being rebuilt from nothing, and the
    # changed set otherwise. `force` asks for the first by name.
    whole = force or bool(report.rebuilt)
    targets = metas if whole else [*changes.added, *changes.changed]
    stale = sorted({meta.rel_path for meta in targets} | set(changes.removed))

    facts = _facts(root, targets)
    report.parsed = len(facts)
    report.errors = {p: f.error for p, f in facts.items() if f.error}
    table = symtab.build({p: f for p, f in facts.items() if not f.error})

    # One transaction per pass, and never one per file. `store.stamp` is the
    # witness that the graph matches the algorithm, and there is no such point if
    # each file commits alone. A reader under WAL sees the before or the after.
    with conn:
        indexwrite.forget_files(conn, stale)
        file_ids = indexwrite.write_files(conn, targets, facts)
        nodes = indexwrite.write_nodes(conn, table, file_ids)

        # The file-local split. A reference its own file already decides is an
        # edge, and every other one is a `refs` row the query resolves on read.
        # Neither branch reads a second file, which is the whole invariant.
        progress.phase("resolving")
        decided: dict[str, list[resolve.Resolution]] = {}
        deferred: dict[str, list[extract.Reference]] = {}
        for p, file_facts in table.files.items():
            decided[p], deferred[p] = resolve.resolve_file_local(p, file_facts)
        indexwrite.write_refs(conn, deferred, file_ids)
        indexwrite.write_imports(conn, facts, file_ids)

        edges = indexwrite.structural_edges(table, nodes)
        for p, rows in decided.items():
            edges += indexwrite.reference_edges(p, rows, nodes)
        indexwrite.write_edges(conn, edges)
        indexwrite.write_fts(conn, file_ids.values())
        # Measured on `go-monorepo`, 2026-09-01: the overlay is 49 s of a 58 s hinted
        # pass, because it re-runs the indexer and re-reads 1.8 M occurrences
        # whatever changed. It has no per-file form, so it rides the reconciler
        # the way `reclaim` does, and a hinted save carries no `scip` tier until
        # the next unhinted pass.
        if not report.hinted:
            report.scip = _overlay(conn, root, cfg)
        if report.scip:
            # The overlay updates `qualified_name` and can insert nodes, and
            # neither reaches an external-content index. It has no per-file
            # write of its own, so it still pays for the whole rebuild.
            indexwrite.rebuild_fts(conn)
        store.stamp(conn)

    totals = store.counts(conn)
    if whole:
        # A truncating checkpoint is fsync-bound, and after stage 2 a pass runs
        # on every save. The pages worth reclaiming are the ones a whole-tree
        # rewrite freed, so the whole-tree pass is where the call belongs.
        store.reclaim(conn)
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
        # A hinted pass saw the languages the hint named, and writing those as
        # the project's capabilities would narrow the row to one save's worth.
        if not report.hinted:
            caps = {lang: sorted(grammars.capabilities(lang)) for lang in report.languages}
    registry.mark_indexed(report.root, counts=counts, capabilities=caps)
