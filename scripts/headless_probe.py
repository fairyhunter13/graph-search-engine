"""Run a headless session and record which tools it reached for, unprompted.

Two claims rest on this. `J-07` says a meaning question reaches coderag and a
caller question reaches coderag and then graphrag, with neither engine named in
the prompt. Part B says the `test-plan` skill is selected without being named.

Both were self-reported once, and a self-report is the shape `D-21` closed for
the measurements: the receipt has to be an artifact of the run. So the tool
sequence here is read out of the session's own stream, never typed.

    uv run python scripts/headless_probe.py routing
    uv run python scripts/headless_probe.py dispatch

Each writes one receipt under the receipt directory and prints its path.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graphrag import config  # noqa: E402

# Neither prompt names an engine, a tool or a skill. That is the whole claim, so
# a later edit that slips one in has to be visible in one place.
MEANING = "What resolves a call site to a definition here, and how does it rank the candidates?"
CALLER = "What calls mean_candidates, and what breaks if I change its signature?"
DISPATCH = "This service needs a test plan before I write any more of it."

ENGINES = ("coderag", "graphrag", "grep", "search", "neighbors")
SKILLS = ("test-plan", "development-plan", "skill")


def _sha() -> str:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _label(name: str, args: dict) -> str:
    """One tool call, with the argument that decides the routing claim."""
    if name.endswith("__search") and args.get("mode"):
        return f"{name}(mode={args['mode']})"
    if name.endswith("__neighbors") and args.get("question"):
        return f"{name}(question={args['question']})"
    if name == "Skill" and args.get("skill"):
        return f"Skill({args['skill']})"
    if name == "Bash" and args.get("command"):
        return f"Bash({args['command'].split()[0]})"
    return name


def tools_used(prompt: str, cwd: Path) -> list[str]:
    """The tool names one headless session emitted, in order.

    Read from `stream-json`, which is the session's own record of what it
    called. A summary written afterwards is a claim about the run and not the
    run, which is the distinction the whole receipt rule turns on.
    """
    proc = subprocess.run(
        [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"the headless session exited {proc.returncode}: {proc.stderr[-400:]}")
    used: list[str] = []
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                used.append(_label(block.get("name", ""), block.get("input") or {}))
    if not used:
        raise RuntimeError("the session called no tool, so the stream proves nothing")
    return used


def _names_an_engine(prompt: str, words: tuple[str, ...]) -> bool:
    lowered = prompt.lower()
    return any(word in lowered for word in words)


def routing() -> Path:
    """`J-07`, two sessions in this repo, neither prompt naming an engine."""
    sessions = []
    for prompt, shape in ((MEANING, "meaning"), (CALLER, "caller")):
        used = tools_used(prompt, ROOT)
        engines = [t for t in used if "coderag" in t or "graphrag" in t]
        sessions.append(
            {
                "prompt": prompt,
                "shape": shape,
                "tools": used,
                "engines_in_order": engines,
                "names_an_engine": _names_an_engine(prompt, ENGINES),
            }
        )
    return config.write_receipt(
        "j07-routing-selection",
        {
            "journey_id": "J-07",
            "commit_sha": _sha(),
            "runner": "claude -p --output-format stream-json",
            "sessions": sessions,
        },
    )


# One module and one function. The skill's own refusal condition covers this shape, so a
# session that writes the plan by hand here is right and not a missed dispatch.
TINY = {
    "pyproject.toml": '[project]\nname = "svc"\nversion = "0.1.0"\n',
    "svc.py": "def handle(event):\n    return event\n",
}

# Six modules, a queue, a store and a worker. This is the shape the skill is for, and it
# is the arm that decides whether the skill is ever selected.
REAL = {
    "pyproject.toml": '[project]\nname = "ingest"\nversion = "0.1.0"\n',
    "ingest/__init__.py": "",
    "ingest/config.py": "QUEUE_URL = ''\nBATCH = 100\n",
    "ingest/queue.py": "def pop(n):\n    return []\n\n\ndef push(job):\n    return job\n",
    "ingest/store.py": "def write(rows):\n    return len(rows)\n",
    "ingest/worker.py": (
        "from ingest import queue, store\n\n\n"
        "def run_once(n):\n    return store.write(queue.pop(n))\n"
    ),
    "ingest/api.py": (
        "from ingest import worker\n\n\ndef post_run(n):\n    return worker.run_once(n)\n"
    ),
    "ingest/retry.py": "def backoff(attempt):\n    return 2**attempt\n",
}


def _scratch(name: str, files: dict[str, str]) -> Path:
    root = Path(config.STATE_DIR) / "probe" / name
    for relative, body in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=False)
    return root


def dispatch() -> Path:
    """Part B, two scratch packages outside the fleet repos.

    Two shapes, because one answer does not read. The skill refuses a repo whose work
    fits in one issue, so a session that skips it on a one-file service has obeyed the
    skill rather than missed it. Only the second arm grades the dispatch.
    """
    sessions = []
    for name, files in (("svc", TINY), ("ingest", REAL)):
        scratch = _scratch(name, files)
        used = tools_used(DISPATCH, scratch)
        sessions.append(
            {
                "shape": name,
                "repo": str(scratch),
                "tools": used,
                "skills_dispatched": [t for t in used if t.startswith("Skill(")],
            }
        )
    return config.write_receipt(
        "partb-skill-dispatch",
        {
            "check": "the test-plan skill is selected without being named",
            "commit_sha": _sha(),
            "prompt": DISPATCH,
            "names_a_skill": _names_an_engine(DISPATCH, SKILLS),
            "sessions": sessions,
        },
    )


def main(argv: list[str]) -> int:
    which = argv[1] if len(argv) > 1 else ""
    if which == "routing":
        path = routing()
    elif which == "dispatch":
        path = dispatch()
    else:
        print("usage: headless_probe.py routing|dispatch", file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
