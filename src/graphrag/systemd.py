"""Per-user units, written and enabled by the CLI.

`Type=notify` is the load-bearing line. Without it systemd calls the unit
started as soon as the process forks, and the first session's tool call races a
daemon whose store is not open yet. The daemon sends READY after the worker runs
and the queue is served, so started means answerable.

The caps are set with the semantic engine already running on this machine. Two
indexers competing with the editor for the same cores is the load this unit is
shaped around, and the second one to arrive takes the smaller share.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import config

UNIT_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "systemd" / "user"

SERVICE = "graphrag.service"
HEALTH = "graphrag-health.service"
HEALTH_TIMER = "graphrag-health.timer"
DOCTOR = "graphrag-doctor.service"
DOCTOR_TIMER = "graphrag-doctor.timer"
ALERT = "graphrag-alert@.service"

# Enabled by name. The two services behind the timers are started by them and
# never enabled on their own, or a boot runs a check nothing asked for.
ENABLE = (SERVICE, HEALTH_TIMER, DOCTOR_TIMER)


def _binary() -> str:
    """The console script, by absolute path. A unit inherits no PATH worth using."""
    return shutil.which("graphrag") or str(Path.cwd() / ".venv" / "bin" / "graphrag")


def units(binary: str = "") -> dict[str, str]:
    """Every unit file, keyed by name. Rendered, never templated on disk."""
    exe = binary or _binary()
    return {
        SERVICE: f"""\
[Unit]
Description=graphrag code graph daemon
OnFailure=graphrag-alert@%n.service

[Service]
Type=notify
ExecStart={exe} serve
Restart=on-failure
RestartSec=5
TimeoutStopSec=20
Environment=GRAPHRAG_PORT={config.PORT}
Nice=12
CPUWeight=15
IOWeight=15
MemoryHigh=2G

[Install]
WantedBy=default.target
""",
        HEALTH: f"""\
[Unit]
Description=graphrag health check
OnFailure=graphrag-alert@%n.service

[Service]
Type=oneshot
ExecStart={exe} health
""",
        HEALTH_TIMER: """\
[Unit]
Description=graphrag health check, hourly

[Timer]
OnUnitActiveSec=3600s
OnBootSec=300s

[Install]
WantedBy=timers.target
""",
        DOCTOR: f"""\
[Unit]
Description=graphrag capability report

[Service]
Type=oneshot
ExecStart={exe} doctor
# A doctor that finds a problem is not a unit that failed. Exit 1 is a finding,
# and treating it as a failure pages for the report rather than the fault.
SuccessExitStatus=0 1
""",
        DOCTOR_TIMER: """\
[Unit]
Description=graphrag capability report, daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
""",
        ALERT: """\
[Unit]
Description=graphrag alert for %i

[Service]
Type=oneshot
# The desktop session is not always ready when a boot-time failure fires, and a
# notification sent into nothing is a failure nobody sees.
ExecStartPre=/bin/sleep 8
ExecStart=/usr/bin/notify-send -u critical "graphrag" "%i failed"
""",
    }


def write(directory: Path | None = None, binary: str = "") -> list[Path]:
    """Write every unit. Returns the paths, in the order they were written."""
    target = directory or UNIT_DIR
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in units(binary).items():
        path = target / name
        path.write_text(text)
        written.append(path)
    return written


def _systemctl(*args: str) -> tuple[int, str]:
    try:
        done = subprocess.run(
            ["systemctl", "--user", *args], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return done.returncode, (done.stderr or done.stdout).strip()


def install(directory: Path | None = None, binary: str = "") -> dict[str, object]:
    """Write the units, reload, and enable the three that are enabled by name."""
    written = write(directory, binary)
    steps: list[dict[str, object]] = []
    for args in (("daemon-reload",), ("enable", "--now", *ENABLE)):
        code, said = _systemctl(*args)
        steps.append({"command": " ".join(args), "code": code, "said": said})
    return {"written": [str(p) for p in written], "steps": steps}


def uninstall(directory: Path | None = None) -> dict[str, object]:
    """Stop and disable the units, then remove the files this module wrote."""
    code, said = _systemctl("disable", "--now", *ENABLE)
    target = directory or UNIT_DIR
    removed = []
    for name in units():
        path = target / name
        if path.exists():
            path.unlink()
            removed.append(str(path))
    _systemctl("daemon-reload")
    return {"removed": removed, "code": code, "said": said}
