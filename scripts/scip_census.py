"""The three SCIP figures Stage 6 named and the tree does not hold.

`the-scip-tier-reports-before-it-acts.md` carries a tier census taken by a loop
that was never committed, so the numbers could be read and not re-run. These
arms are that loop, and two more the exit criteria asked for.

    uv run python scripts/scip_census.py tiers
    uv run python scripts/scip_census.py share
    uv run python scripts/scip_census.py overlay
    uv run python scripts/scip_census.py all

A receipt carries counts and never a filesystem path. `.github/workflows/ci.yml`
cats the receipt directory into a public log, and this fleet is private
repositories, so a root appears here only as a digest of its resolved path.

This is a script and not a `cli.py` subcommand because `src/graphrag/cli.py` is
exactly at the 300-line module ceiling, and because the fleet form of the report
was cut: family grouping only ever mattered to a census nobody ships.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graphrag import config, registry, store  # noqa: E402
from graphrag.scip import overlay as apply_overlay  # noqa: E402
from graphrag.scip import run  # noqa: E402


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha() -> str:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _label(path: Path | str) -> str:
    """A root's stable name in a public log. The path itself is private."""
    return hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()[:12]


def _write(name: str, receipt: dict) -> Path:
    receipt.setdefault("commit_sha", _sha())
    receipt.setdefault("written_at", _now())
    with config.receipt_lock(name):
        return config.write_receipt(name, receipt)


def _enabled() -> list[Path]:
    return [Path(row.path) for row in registry.load().values() if row.enabled]


def _languages(path: Path) -> list[str]:
    """The languages tree-sitter found, from the store's own file census."""
    graph = config.index_path(path)
    if not graph.exists():
        return []
    conn = store.connect(graph, create=False)
    try:
        rows = conn.execute("SELECT DISTINCT lang FROM files WHERE lang != ''")
        return sorted(row[0] for row in rows)
    except sqlite3.DatabaseError:
        return []
    finally:
        conn.close()


def _family(path: Path) -> str:
    """The main repository a worktree belongs to, or the root itself.

    A worktree's `.git` is a *file* holding one `gitdir:` line, so the family
    key is one file read. `git rev-parse --git-common-dir` is one subprocess
    per root to learn what that line already says.
    """
    dot = path / ".git"
    try:
        if dot.is_file():
            for line in dot.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("gitdir:"):
                    raw = line.split(":", 1)[1].strip()
                    marker = "/.git/worktrees/"
                    if marker in raw:
                        return _label(raw.split(marker, 1)[0])
                    return _label(raw)
    except OSError:
        pass
    return _label(path)


def _best(seen: list[str]) -> str:
    """`run.TIERS` is ordered best first, so a family stands at its best root."""
    return min(seen, key=run.TIERS.index)


# ------------------------------------------------------------------ 1. tiers


def tiers() -> Path:
    """The tier census, under both denominators.

    The committed table counts indexer/root pairs and never said so. A family
    is a repository and its worktrees, which is the denominator an operator
    acts on: a worktree needs no separate install.
    """
    roots = _enabled()
    pairs: dict[str, int] = dict.fromkeys(run.TIERS, 0)
    families: dict[tuple[str, str], list[str]] = {}
    no_store = 0
    for path in roots:
        langs = _languages(path)
        if not langs:
            no_store += 1
            continue
        key = _family(path)
        for standing in run.readiness(path, langs):
            tier = str(standing["tier"])
            pairs[tier] += 1
            families.setdefault((key, str(standing["indexer"])), []).append(tier)
    grouped: dict[str, int] = dict.fromkeys(run.TIERS, 0)
    for seen in families.values():
        grouped[_best(seen)] += 1
    return _write(
        "scip-census-tiers",
        {
            "check": "every enabled root's SCIP standing, per indexer/root pair and per family",
            "roots_enabled": len(roots),
            "roots_with_no_store": no_store,
            "families": len({key for key, _ in families}),
            "pairs_total": sum(pairs.values()),
            "pairs_by_tier": pairs,
            "family_pairs_total": sum(grouped.values()),
            "family_pairs_by_tier": grouped,
            "grouping": "a family stands at the best tier any of its roots reaches",
        },
    )


# ------------------------------------------------------------------ 2. share


def share() -> Path:
    """What share of the fleet's CALLS edges a compiler decided.

    `dbread.decided_by_scip` answers this per file and returns a bool. Nothing
    committed asks it of the fleet, so the exit's before and after had no
    figure to move.
    """
    roots = _enabled()
    total: dict[str, int] = {}
    read = 0
    for path in roots:
        graph = config.index_path(path)
        if not graph.exists():
            continue
        conn = store.connect(graph, create=False)
        try:
            rows = conn.execute(
                "SELECT evidence, count(*) FROM edges WHERE kind='CALLS' GROUP BY evidence"
            ).fetchall()
        except sqlite3.DatabaseError:
            continue
        finally:
            conn.close()
        read += 1
        for evidence, count in rows:
            total[str(evidence)] = total.get(str(evidence), 0) + int(count)
    calls = sum(total.values())
    scip = total.get("scip", 0)
    return _write(
        "scip-census-share",
        {
            "check": "the share of the fleet's CALLS edges carrying evidence 'scip'",
            "roots_enabled": len(roots),
            "stores_read": read,
            "stores_skipped": len(roots) - read,
            "calls_total": calls,
            "calls_by_evidence": dict(sorted(total.items())),
            "scip_calls": scip,
            "scip_share_pct": round(100 * scip / calls, 4) if calls else 0.0,
        },
    )


# ------------------------------------------------------------------ 3. overlay


def _porcelain(path: Path) -> int:
    out = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    return len([line for line in out.stdout.splitlines() if line.strip()])


def overlay() -> Path:
    """Apply the tier where it needs no install, and refuse it everywhere else.

    The refusal is the safety property. `installable` is reachable only by
    running a package manager inside a repository this engine does not own, and
    that install deletes and reinstalls the dependency tree, so that population
    is unreachable from this surface by construction -- the way `deps.check`
    refuses a command with no `--ignore-scripts`.

    Nothing is written into a project either. `scip.overlay` puts its index
    beside the graph, and the working tree is counted before and after to say
    so rather than to assume it.
    """
    done = []
    refused = 0
    for path in _enabled():
        langs = _languages(path)
        if not langs:
            continue
        ready = [str(s["indexer"]) for s in run.readiness(path, langs) if s["tier"] == "ready"]
        if not ready:
            refused += 1
            continue
        before = _porcelain(path)
        conn = store.connect(config.index_path(path), create=False)
        try:
            said = apply_overlay(conn, path, ready)
            conn.commit()
        finally:
            conn.close()
        after = _porcelain(path)
        done.append(
            {
                "root": _label(path),
                "indexers": ready,
                "outcome": said,
                "worktree_entries_before": before,
                "worktree_entries_after": after,
                "worktree_unchanged": before == after,
            }
        )
    return _write(
        "scip-census-overlay",
        {
            "check": "the overlay applied to every root already at tier ready, and no other",
            "applied": len(done),
            "refused_not_ready": refused,
            "roots": done,
            "all_worktrees_unchanged": all(row["worktree_unchanged"] for row in done),
        },
    )


ARMS = {"tiers": tiers, "share": share, "overlay": overlay}


def main(argv: list[str]) -> int:
    which = argv[1] if len(argv) > 1 else ""
    if which == "all":
        for arm in ARMS.values():
            print(arm())
        return 0
    if which not in ARMS:
        print(f"usage: scip_census.py {'|'.join(ARMS)}|all", file=sys.stderr)
        return 2
    path = ARMS[which]()
    print(path)
    print(json.dumps(json.loads(Path(path).read_text()), indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
