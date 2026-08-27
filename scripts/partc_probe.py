"""Measure the four part C claims that no evidence stood behind.

An audit found four verification bullets self-reported. `D-21` closed that
shape once: a claim is graded against a receipt the run itself wrote, never
against a sentence written afterwards.

Each arm here touches the real machine. Real hooks, the real units, the real
profile files and a real bound socket. Nothing is mocked, so an arm that cannot
run on this machine writes no receipt and the test skips.

    uv run python scripts/partc_probe.py reach
    uv run python scripts/partc_probe.py notify
    uv run python scripts/partc_probe.py profiles
    uv run python scripts/partc_probe.py port
    uv run python scripts/partc_probe.py all

Each writes one receipt under the receipt directory and prints its path.
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graphrag import config  # noqa: E402

CCW = Path("/home/<user>/go/src/github.com/fairyhunter13/claude-code-workflows/bin/ccw")
GRAPHRAG_CLI = ROOT / ".venv" / "bin" / "graphrag"
SERVICE = "graphrag.service"

# The five files a launcher reads. `~/.claude/.claude.json` is not one of them.
# It is a decoy, and the receipt records it as one, because an omitted row reads
# as a file nobody checked.
PROFILES = (
    Path.home() / ".claude.json",
    Path.home() / ".claude-1" / ".claude.json",
    Path.home() / ".claude-2" / ".claude.json",
    Path.home() / ".claude-3" / ".claude.json",
    Path.home() / ".claude-4" / ".claude.json",
)
DECOY = Path.home() / ".claude" / ".claude.json"

GRAPH_COUNTS = re.compile(r"([\d,]+) nodes, ([\d,]+) edges, (\d+)% of them resolved")
CODE_COUNTS = re.compile(r"([\d,]+) files, ([\d,]+) chunks")


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


def _run(cmd: list[str], cwd: Path | None = None, timeout: float = 120.0):
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout
    )


def _write(name: str, receipt: dict) -> Path:
    path = config.RECEIPT_DIR / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt.setdefault("commit_sha", _sha())
    receipt.setdefault("written_at", _now())
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return path


def _int(raw: str) -> int:
    return int(raw.replace(",", ""))


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _port_taken(host: str, port: int) -> bool:
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return True
    return False


def _get(url: str, timeout: float = 10.0) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as answer:
            return {"status": answer.status, "body": answer.read().decode("utf-8")[:400]}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body": exc.read().decode("utf-8")[:400]}
    except OSError as exc:
        return {"status": 0, "error": str(exc)}


def _initialize(url: str, timeout: float = 15.0) -> dict:
    """One MCP `initialize` against the URL a profile names."""
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "partc_probe", "version": "0"},
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return {"status": answer.status, "body": answer.read().decode("utf-8")[:400]}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body": exc.read().decode("utf-8")[:400]}
    except OSError as exc:
        return {"status": 0, "error": str(exc)}


# ------------------------------------------------------------------ 1. reach


def _notice(hook: str) -> dict:
    out = _run([str(CCW), "hook", hook], cwd=ROOT, timeout=120)
    text = ""
    if out.returncode == 0 and out.stdout.strip():
        try:
            text = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
        except (json.JSONDecodeError, KeyError, TypeError):
            text = ""
    return {
        "hook": hook,
        "exit_code": out.returncode,
        "stderr": out.stderr[-400:],
        "notice": text,
        "present": bool(text.strip()),
    }


def _graphrag_cli_counts() -> dict:
    out = _run([str(GRAPHRAG_CLI), "status"], cwd=ROOT, timeout=120)
    row = json.loads(out.stdout)["rows"][str(ROOT)]
    edges, resolved = row["edge_count"], row["resolved_edge_count"]
    return {
        "nodes": row["node_count"],
        "edges": edges,
        "resolved_edges": resolved,
        "resolved_pct": round(100 * resolved / edges) if edges else 0,
    }


def _coderag_cli_counts() -> dict:
    binary = shutil.which("coderag")
    if not binary:
        raise RuntimeError("no coderag on PATH, so the notice has nothing to be checked against")
    out = _run([binary, "list"], timeout=120)
    for line in out.stdout.splitlines():
        fields = line.split()
        if fields and fields[-1] == str(ROOT):
            return {"files": int(fields[-3]), "chunks": int(fields[-2])}
    raise RuntimeError(f"`coderag list` names no row for {ROOT}")


def reach() -> Path:
    """Both SessionStart notices, against what each engine's own CLI reports."""
    notices = {name: _notice(f"{name}-reach") for name in ("coderag", "graphrag")}
    graph_seen = GRAPH_COUNTS.search(notices["graphrag"]["notice"])
    code_seen = CODE_COUNTS.search(notices["coderag"]["notice"])
    graph_cli, code_cli = _graphrag_cli_counts(), _coderag_cli_counts()

    graph_notice = (
        {
            "nodes": _int(graph_seen.group(1)),
            "edges": _int(graph_seen.group(2)),
            "resolved_pct": int(graph_seen.group(3)),
        }
        if graph_seen
        else {}
    )
    code_notice = (
        {"files": _int(code_seen.group(1)), "chunks": _int(code_seen.group(2))} if code_seen else {}
    )
    return _write(
        "partc-reach-counts",
        {
            "check": "both reach notices appear, and each count matches that engine's own CLI",
            "root": str(ROOT),
            "both_present": all(entry["present"] for entry in notices.values()),
            "notices": notices,
            "engines": {
                "graphrag": {
                    "notice": graph_notice,
                    "cli": graph_cli,
                    "matches": bool(graph_notice)
                    and graph_notice["nodes"] == graph_cli["nodes"]
                    and graph_notice["edges"] == graph_cli["edges"]
                    and graph_notice["resolved_pct"] == graph_cli["resolved_pct"],
                },
                "coderag": {
                    "notice": code_notice,
                    "cli": code_cli,
                    "matches": bool(code_notice)
                    and code_notice["files"] == code_cli["files"]
                    and code_notice["chunks"] == code_cli["chunks"],
                },
            },
        },
    )


# ----------------------------------------------------------------- 2. notify


def _is_active() -> str:
    return _run(["systemctl", "--user", "is-active", SERVICE], timeout=30).stdout.strip()


def notify() -> Path:
    """A clean stop, then a start, and healthz on the first `active` sample.

    A restart is not measurable here. The outgoing instance can still hold the
    port while the new one binds, so the reading would grade the old daemon.
    """
    stop = _run(["systemctl", "--user", "stop", SERVICE], timeout=120)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and (
        _is_active() == "active" or _port_taken(config.HOST, config.PORT)
    ):
        time.sleep(0.05)
    stopped_state = _is_active()
    port_free_after_stop = not _port_taken(config.HOST, config.PORT)
    healthz_while_stopped = _get(config.HEALTHZ_URL, timeout=3)

    began = time.monotonic()
    issued_at = _now()
    starting = subprocess.Popen(
        ["systemctl", "--user", "start", SERVICE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    active_at: float | None = None
    samples: list[str] = []
    while time.monotonic() - began < 120:
        state = _is_active()
        samples.append(state)
        if state == "active":
            active_at = time.monotonic()
            break
        time.sleep(0.01)

    # One attempt, never a retry loop. A retry proves the daemon answers
    # eventually, and the claim is that it answers already.
    healthz = _get(config.HEALTHZ_URL, timeout=10)
    healthz_at = time.monotonic()

    answering = healthz
    while answering.get("status") != 200 and time.monotonic() - began < 120:
        time.sleep(0.005)
        answering = _get(config.HEALTHZ_URL, timeout=10)
    answered_at = time.monotonic()
    starting.wait(timeout=120)
    if _is_active() != "active":
        _run(["systemctl", "--user", "start", SERVICE], timeout=120)

    return _write(
        "partc-notify-order",
        {
            "check": "systemd reports started only once the daemon answers healthz",
            "unit": SERVICE,
            "healthz_url": config.HEALTHZ_URL,
            "stop": {
                "exit_code": stop.returncode,
                "state_after": stopped_state,
                "port_free_after_stop": port_free_after_stop,
                "healthz_while_stopped": healthz_while_stopped,
            },
            "start": {
                "issued_at": issued_at,
                "exit_code": starting.returncode,
                "states_sampled": samples[:40],
                "seconds_to_active": None if active_at is None else round(active_at - began, 4),
                "seconds_to_healthz": round(healthz_at - began, 4),
                "reached_active": active_at is not None,
            },
            "healthz_on_first_active_sample": healthz,
            "healthz_answered": answering,
            "seconds_from_active_to_answer": (
                None if active_at is None else round(answered_at - active_at, 4)
            ),
            "answers_on_first_active_sample": healthz.get("status") == 200,
            "left_running": _is_active() == "active",
        },
    )


# --------------------------------------------------------------- 3. profiles


def profiles() -> Path:
    """The five real profile files, and whether the URL each names answers."""
    rows = []
    for path in PROFILES:
        row: dict = {"path": str(path), "exists": path.is_file()}
        if row["exists"]:
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                row["parse_error"] = str(exc)
                loaded = {}
            servers = loaded.get("mcpServers") or {}
            entry = servers.get("graphrag") or {}
            row["server_names"] = sorted(servers)
            row["has_graphrag"] = bool(entry)
            row["url"] = entry.get("url", "")
            row["transport"] = entry.get("type", "")
        rows.append(row)

    decoy = {
        "path": str(DECOY),
        "exists": DECOY.is_file(),
        "read_by_a_launcher": False,
        "note": "a decoy: no launcher reads it, so what it holds grades nothing",
    }
    if decoy["exists"]:
        loaded = json.loads(DECOY.read_text(encoding="utf-8"))
        decoy["server_names"] = sorted(loaded.get("mcpServers") or {})

    urls = sorted({row.get("url", "") for row in rows if row.get("url")})
    answers = {
        url: {
            "mcp_initialize": _initialize(url),
            "healthz": _get(url[: -len("/mcp")] + "/healthz" if url.endswith("/mcp") else url),
        }
        for url in urls
    }
    return _write(
        "partc-five-profiles",
        {
            "check": "each real profile names the graphrag server, and that URL answers",
            "profiles": rows,
            "decoy": decoy,
            "urls": urls,
            "answers": answers,
        },
    )


# ------------------------------------------------------------------- 4. port


def _refusal(host: str, port: int) -> dict:
    out = _run([str(GRAPHRAG_CLI), "serve", "--host", host, "--port", str(port)], timeout=120)
    message = (out.stderr + out.stdout).strip()
    return {
        "host": host,
        "port": port,
        "exit_code": out.returncode,
        "message": message[-400:],
        "names_the_port": str(port) in message,
        "refused": out.returncode != 0,
    }


def port() -> Path:
    """A taken port is a refusal that names it, never a silent rebind.

    The plan claimed 8766 was free before the first apply, and the daemon now
    owns the port, so nobody can take that reading again. This measures the
    invariant the claim was reaching for, and that is measurable today.
    """
    scratch = _free_port()
    held = socket.socket()
    held.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    held.bind(("127.0.0.1", scratch))
    held.listen(1)
    try:
        scratch_arm = _refusal("127.0.0.1", scratch)
    finally:
        held.close()

    live_arm = _refusal(config.HOST, config.PORT)
    return _write(
        "partc-port-refusal",
        {
            "check": "the daemon refuses a taken port and names it, rather than rebinding",
            "scratch": scratch_arm,
            "scratch_free_after_release": not _port_taken("127.0.0.1", scratch),
            "live": live_arm,
            "daemon_still_answers": _get(config.HEALTHZ_URL),
            "unit_state": _is_active(),
        },
    )


ARMS = {"reach": reach, "notify": notify, "profiles": profiles, "port": port}


def main(argv: list[str]) -> int:
    which = argv[1] if len(argv) > 1 else ""
    if which == "all":
        for arm in ARMS.values():
            print(arm())
        return 0
    if which not in ARMS:
        print(f"usage: partc_probe.py {'|'.join(ARMS)}|all", file=sys.stderr)
        return 2
    print(ARMS[which]())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
