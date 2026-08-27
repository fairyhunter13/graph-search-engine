"""J-08: the caller-question set, scored against hand-verified edges.

The routing rule says coderag names the symbol and graphrag walks the edges
from it. No record measured that, so the rule was argued and never graded.

Ground truth is hand-verified over the whole tracked tree, `tests/` and
`scripts/` included. A caller there is a caller, and scoping it out of the
truth prices a correct answer as a false positive.

Every case carries a class, and the classes are the finding. A `distinctive`
name is called only through the module that defines it. A `collides` name is
also an attribute of something else in this tree -- `list.append`,
`Path.resolve`, `sqlite3.connect`. Before `D-19` the extractor discarded the
receiver, so the two were one name and the `collides` class collapsed. The
receiver now names the module, and the classes stay split because a receiver
that names a local variable is refused rather than placed.

Scoring is at file granularity, because that is the coarsest unit both engines
answer in -- coderag returns a chunk, graphrag returns a node, and a file holds
both.

Run: `uv run python scripts/two_engine_measure.py`. It needs the coderag daemon.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from graphrag import config, query, registry, store

ROOT = Path(__file__).resolve().parents[1]

DISTINCTIVE = "distinctive"
COLLIDES = "collides"

# symbol -> the file that defines it, and every file that calls it. Read, not
# generated: a generated ground truth grades the generator. The census behind
# each row is `<module>.<name>(` over `git ls-files`, then read by hand.
TRUTH: list[dict] = [
    {
        "name": "resolve",
        "class": COLLIDES,  # Path.resolve, and two local variables
        "defined_in": "src/graphrag/registry.py",
        "callers": [
            "src/graphrag/registry.py",
            "src/graphrag/cli.py",
            "src/graphrag/federation.py",
            "src/graphrag/reach.py",
            "src/graphrag/scope.py",
            "src/graphrag/tools.py",
            "tests/test_registry.py",
            "tests/test_systemd.py",
            "scripts/two_engine_measure.py",
        ],
    },
    {
        "name": "index_path",
        "class": DISTINCTIVE,
        "defined_in": "src/graphrag/config.py",
        "callers": [
            "src/graphrag/cli.py",
            "src/graphrag/index.py",
            "src/graphrag/progress.py",
            "src/graphrag/registry.py",
            "src/graphrag/tools.py",
            "tests/test_index.py",
            "scripts/two_engine_measure.py",
            "tests/test_two_engine.py",
            "tests/test_scip_guard.py",
            "tests/test_scip_ingest.py",
            "tests/test_scip_run.py",
        ],
    },
    {
        "name": "load",
        "class": COLLIDES,  # projcfg.load, yaml.load
        "defined_in": "src/graphrag/registry.py",
        "callers": [
            "src/graphrag/registry.py",
            "src/graphrag/cli.py",
            "src/graphrag/federation.py",
            "src/graphrag/scope.py",
            "src/graphrag/server.py",
            "src/graphrag/watch.py",
            "tests/test_registry.py",
        ],
    },
    {
        "name": "append",
        "class": COLLIDES,  # every list in the tree
        "defined_in": "src/graphrag/ledger.py",
        "callers": [
            "src/graphrag/index.py",
            "src/graphrag/server.py",
            "src/graphrag/watch.py",
            "tests/test_watch.py",
        ],
    },
    {
        "name": "counts",
        "class": DISTINCTIVE,
        "defined_in": "src/graphrag/store.py",
        "callers": [
            "src/graphrag/index.py",
            "src/graphrag/query.py",
            "tests/test_index.py",
            "tests/test_store.py",
        ],
    },
    {
        "name": "capabilities",
        "class": DISTINCTIVE,
        "defined_in": "src/graphrag/grammars.py",
        "callers": [
            "src/graphrag/grammars.py",
            "src/graphrag/cli.py",
            "src/graphrag/index.py",
            "src/graphrag/query.py",
            "tests/test_grammars.py",
            "tests/test_import_queries.py",
        ],
    },
    {
        "name": "capability_report",
        "class": DISTINCTIVE,
        "defined_in": "src/graphrag/query.py",
        "callers": [
            "src/graphrag/query.py",
            "src/graphrag/cli.py",
            "src/graphrag/tools.py",
            "tests/test_index.py",
        ],
    },
    {
        "name": "connect",
        "class": COLLIDES,  # sqlite3.connect, socket.connect
        "defined_in": "src/graphrag/store.py",
        "callers": [
            "src/graphrag/cli.py",
            "src/graphrag/index.py",
            "src/graphrag/tools.py",
            "tests/test_index.py",
            "tests/test_store.py",
            "scripts/two_engine_measure.py",
            "tests/test_two_engine.py",
            "tests/test_scip_guard.py",
            "tests/test_scip_ingest.py",
            "tests/test_scip_run.py",
        ],
    },
    {
        "name": "language_of",
        "class": DISTINCTIVE,
        "defined_in": "src/graphrag/filters.py",
        "callers": [
            "src/graphrag/filters.py",
            "src/graphrag/discover.py",
            "src/graphrag/watch.py",
        ],
    },
    {
        "name": "index_once",
        "class": DISTINCTIVE,
        "defined_in": "src/graphrag/index.py",
        "callers": [
            "src/graphrag/index.py",
            "src/graphrag/cli.py",
            "tests/test_index.py",
            "tests/test_tools.py",
            "tests/test_watch.py",
            "tests/test_two_engine.py",
            "tests/test_scip_guard.py",
            "tests/test_scip_ingest.py",
            "tests/test_scip_run.py",
        ],
    },
]


def graph_callers(conn, case: dict) -> set[str]:
    """One hop upstream on CALLS, from the node the case names."""
    start = None
    for hit in query.find_symbol(conn, case["name"], limit=50):
        if hit.path == case["defined_in"] and hit.kind in {"function", "method"}:
            start = hit.node_id
            break
    if start is None:
        return set()
    return {r.path for r in query.neighbors(conn, start, question="callers").results}


def coderag_files(question: str, mode: str) -> set[str]:
    """The paths one search returns, relative to this root.

    The CLI and not the MCP endpoint: the tool reads its root from the client
    handshake, and a script that posts JSON-RPC sends no workspace roots. The
    CLI takes the root as an argument and runs the same search behind it.
    """
    run = subprocess.run(
        ["coderag", "search", question, str(ROOT), "-k", "10", "--mode", mode],
        capture_output=True,
        text=True,
        check=False,
    )
    start = run.stdout.find("{")
    if start < 0:
        return set()
    try:
        data = json.loads(run.stdout[start:])
    except json.JSONDecodeError:
        return set()
    out = set()
    for hit in data.get("results", []):
        path = hit.get("path", "")
        if path.startswith(str(ROOT)):
            path = str(Path(path).relative_to(ROOT))
        out.add(path)
    return out


ARMS = ("graphrag", "coderag-semantic", "coderag-lexical")


def _tally() -> dict[str, list[int]]:
    return {arm: [0, 0, 0] for arm in ARMS}


def _summary(tally: dict[str, list[int]]) -> dict:
    out = {}
    for arm, (hit, got, want) in tally.items():
        precision = hit / got if got else 0.0
        recall = hit / want if want else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[arm] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "hit": hit,
            "returned": got,
            "truth": want,
        }
    return out


def measure(conn=None) -> dict:
    """The whole receipt, so a caller can assert on it without reading stdout.

    `conn` is a graph of this tree the caller opened. The test passes one it
    built itself, because the suite redirects the state directory and the fleet
    store is not reachable from inside it.
    """
    mine = conn is None
    conn = store.connect(config.index_path(registry.resolve(ROOT)), create=False) if mine else conn
    overall = _tally()
    by_class = {DISTINCTIVE: _tally(), COLLIDES: _tally()}
    rows = []
    try:
        for case in TRUTH:
            truth = set(case["callers"])
            found = {
                "graphrag": graph_callers(conn, case),
                "coderag-semantic": coderag_files(f"what calls {case['name']}", "semantic"),
                "coderag-lexical": coderag_files(case["name"], "lexical"),
            }
            row = {"symbol": case["name"], "class": case["class"], "truth": sorted(truth)}
            for arm, paths in found.items():
                figures = (len(paths & truth), len(paths), len(truth))
                for index, value in enumerate(figures):
                    overall[arm][index] += value
                    by_class[case["class"]][arm][index] += value
                row[arm] = {
                    "hit": figures[0],
                    "returned": figures[1],
                    "truth": figures[2],
                    "extra": sorted(paths - truth),
                    "missed": sorted(truth - paths),
                }
            rows.append(row)
    finally:
        if mine:
            conn.close()

    sha = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    return {
        "commit_sha": sha,
        "corpus": "graph-search-engine",
        "n_questions": len(TRUTH),
        "summary": _summary(overall),
        "by_class": {name: _summary(tally) for name, tally in by_class.items()},
        "per_question": rows,
    }


def main() -> int:
    print(json.dumps(measure(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
