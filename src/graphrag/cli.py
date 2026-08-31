"""The operator surface. Everything the four tools deliberately do not carry.

`doctor` is the one worth naming. It prints the per-language capability table
before anything else, so a session learns which languages in this project answer
a caller question and which do not. Reading that table is what stops an empty
result being read as an absence.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from . import (
    config,
    federation,
    grammars,
    index,
    progress,
    prune,
    quarantine,
    query,
    registry,
    store,
)


def _out(payload: object) -> int:
    json.dump(payload, sys.stdout, indent=2, sort_keys=True, default=str)
    sys.stdout.write("\n")
    return 0


def _open(root: Path) -> tuple[Path, sqlite3.Connection]:
    path = config.index_path(root)
    if not path.exists():
        raise SystemExit(f"{root} has no graph yet, so run `graphrag index` on it first")
    return path, store.connect(path)


def _summary(report: index.IndexReport) -> dict[str, object]:
    return {
        "root": report.root,
        "files": report.files,
        "parsed": report.parsed,
        "nodes": report.nodes,
        "edges": report.edges,
        "resolved": report.resolved,
        "languages": report.languages,
        "rebuilt": report.rebuilt,
        "unchanged": report.unchanged,
        "errors": report.errors,
    }


def cmd_index(args: argparse.Namespace) -> int:
    """Enrol the root and its members, then pass over every one of them.

    A member reached by a symlink is a project of its own, and a row with no
    graph answers nothing. So the fleet pass belongs to the command an operator
    already runs, rather than to a daemon they may not have started.
    """
    root = registry.resolve(args.root)
    if not root.is_dir():
        raise SystemExit(f"{root} is not a directory")
    members = federation.register(root)
    report = index.index_once(root, force=args.force)
    index.record(report)
    out = _summary(report)
    if members:
        rows = []
        for member in members:
            member_report = index.index_once(member, force=args.force)
            index.record(member_report)
            rows.append(_summary(member_report))
        out["members"] = rows
    return _out(out)


def cmd_doctor(args: argparse.Namespace) -> int:
    root = registry.resolve(args.root)
    path, conn = _open(root)
    compacted = None
    try:
        table = query.capability_report(conn)
        counts = query.project_counts(conn)
        if args.compact:
            # Hand-typed, because a full VACUUM rewrites the file and needs free
            # space equal to its size. Stores built before `auto_vacuum` reclaim
            # their freelist no other way.
            before = path.stat().st_size
            store.compact(conn)
            compacted = {"bytes_before": before, "bytes_after": path.stat().st_size}
    finally:
        conn.close()
    # The gaps ride beside the table rather than being left for the reader to
    # derive. A language present in the table with no `calls` is exactly the
    # case that produces a confidently empty caller answer.
    gaps = [
        grammars.missing(lang, "calls")
        for lang in table
        if "calls" not in grammars.capabilities(lang)
    ]
    out = {"root": str(root), "counts": counts, "capabilities": table, "gaps": gaps}
    if compacted is not None:
        out["compacted"] = compacted
    return _out(out)


def cmd_status(_args: argparse.Namespace) -> int:
    rows = registry.load()
    return _out(
        {
            "projects": len(rows),
            "enabled": sum(1 for e in rows.values() if e.enabled),
            "failing": sorted(k for k, e in rows.items() if e.enabled and e.last_error),
            "queue_depth": index.QUEUE.depth,
            "fleet_digest": registry.fleet_digest(rows),
            "unclaimed_stores": [str(p) for p in registry.unclaimed_stores()],
            # A row whose directory is gone was reported nowhere before. Only
            # `missing` is a deletion; the other two are rows this cannot judge.
            "missing": prune.survey(),
            "rows": {k: e.to_json() for k, e in rows.items()},
        }
    )


def cmd_forget(args: argparse.Namespace) -> int:
    """The only thing that removes a row.

    A missing path is not a reason: a project on an unmounted disk is absent,
    not deleted, and pruning it loses the roots that claimed it.
    """
    gone, unknown = registry.forget([str(registry.resolve(p)) for p in args.roots])
    retired = []
    for key in gone:
        # Quarantined, not wiped. `wipe` unlinks the db and leaves the directory
        # standing -- the recorded defect that kept the orphan count off zero --
        # while a move takes the directory with it and stays reversible.
        if quarantine.take(config.index_path(key).parent) is not None:
            retired.append(key)
        progress.path_for(key).unlink(missing_ok=True)
    quarantine.expire()
    return _out({"forgotten": gone, "unknown": unknown, "quarantined": retired})


def _orphan_progress() -> list[Path]:
    """Progress files whose store is gone. They survive `forget` and `prune`."""
    if not config.PROGRESS_DIR.is_dir():
        return []
    live = {p.name for p in config.INDEX_DIR.iterdir() if p.is_dir()} if config.INDEX_DIR.is_dir() else set()
    return sorted(p for p in config.PROGRESS_DIR.glob("*.json") if p.stem not in live)


def cmd_prune(args: argparse.Namespace) -> int:
    """Delete graph directories no registry row names."""
    orphans = _orphan_progress()
    if not args.apply:
        stale = registry.unclaimed_stores()
        return _out(
            {
                "would_delete": [str(p) for p in stale],
                "would_delete_progress": [str(p) for p in orphans],
                "applied": False,
            }
        )
    deleted = registry.prune_unclaimed(force=args.force)
    for path in orphans:
        path.unlink(missing_ok=True)
    expired = quarantine.expire()
    return _out(
        {
            "deleted": [str(p) for p in deleted],
            "deleted_progress": [str(p) for p in orphans],
            "expired_quarantine": [str(p) for p in expired],
            "applied": True,
        }
    )


def cmd_serve(args: argparse.Namespace) -> int:
    from . import server

    server.serve(host=args.host, port=args.port)
    return 0


def cmd_bridge(args: argparse.Namespace) -> int:
    from . import bridge

    return bridge.run(url=args.url, idle_seconds=args.idle)


def cmd_health(args: argparse.Namespace) -> int:
    from . import health

    ok, said = health.check(args.url)
    print(said, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


def cmd_reach(args: argparse.Namespace) -> int:
    from . import reach

    print(reach.notice(args.root, url=args.url))
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    from . import systemd

    return _out(systemd.install(binary=args.binary))


def cmd_uninstall(_args: argparse.Namespace) -> int:
    from . import systemd

    return _out(systemd.uninstall())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=config.APP, description="Structural code search: the operator surface."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("index", help="enrol a project and run one pass now")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--force", action="store_true", help="rebuild even where nothing changed")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("doctor", help="the per-language capability table and the gaps")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--compact", action="store_true", help="VACUUM the graph and report the bytes")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("status", help="every registry row, the queue and the digest")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("forget", help="remove a row and its graph")
    p.add_argument("roots", nargs="+")
    p.set_defaults(func=cmd_forget)

    p = sub.add_parser("prune", help="delete graphs no row claims")
    p.add_argument("--apply", action="store_true", help="delete rather than list")
    p.add_argument("--force", action="store_true", help="allow a verdict over half the tree")
    p.set_defaults(func=cmd_prune)

    p = sub.add_parser("serve", help="run the daemon")
    p.add_argument("--host", default="")
    p.add_argument("--port", type=int, default=0)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("bridge", help="pipe stdio JSON-RPC to the daemon")
    p.add_argument("--url", default="")
    p.add_argument("--idle", type=float, default=0.0)
    p.set_defaults(func=cmd_bridge)

    p = sub.add_parser("health", help="the two-sample check the hourly timer runs")
    p.add_argument("--url", default="")
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("reach", help="enrol this directory and print the session notice")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--url", default="")
    p.set_defaults(func=cmd_reach)

    p = sub.add_parser("install", help="write and enable the per-user units")
    p.add_argument("--binary", default="", help="the console script the units call")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("uninstall", help="disable and remove the per-user units")
    p.set_defaults(func=cmd_uninstall)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
