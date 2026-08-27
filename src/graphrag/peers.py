"""Which process asked, resolved from the source port of its connection.

One daemon serves every session on the machine, so a ledger row saying a pass
was requested names nothing useful without this. The answer is best effort by
construction: a short-lived client is gone before the lookup runs, and `unknown`
is the honest result rather than a guess at the likeliest caller.

Loopback only. A remote peer has no inode in this kernel's tables, so there is
nothing here to leak and nothing to look up.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

UNKNOWN = "unknown"

# Bounded because a port is never reused within a cache lifetime in practice,
# and an unbounded map on a long-lived daemon is a slow leak with no ceiling.
_CACHE_MAX = 512
_CACHE: dict[int, str] = {}


def _inode_for_port(port: int) -> str:
    """The socket inode owning a local source port, over IPv4 and IPv6."""
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        with contextlib.suppress(OSError):
            for line in Path(table).read_text().splitlines()[1:]:
                fields = line.split()
                if len(fields) < 10:
                    continue
                local = fields[1].rsplit(":", 1)
                if len(local) == 2 and int(local[1], 16) == port:
                    return fields[9]
    return ""


def _process_for_inode(inode: str) -> str:
    """The first process holding that socket, as `pid:comm`."""
    target = f"socket:[{inode}]"
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        with contextlib.suppress(OSError):
            for fd in (entry / "fd").iterdir():
                if os.readlink(fd) != target:
                    continue
                comm = (entry / "comm").read_text().strip()
                return f"{entry.name}:{comm}"
    return ""


def by_port(port: int) -> str:
    """The peer on a local source port, or `unknown`. Cached, never raising."""
    if port <= 0:
        return UNKNOWN
    hit = _CACHE.get(port)
    if hit is not None:
        return hit
    inode = _inode_for_port(port)
    found = _process_for_inode(inode) if inode else ""
    answer = found or UNKNOWN
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[port] = answer
    return answer


def of(request) -> str:
    """The peer behind one request, from whatever the transport exposes."""
    client = getattr(request, "client", None)
    port = getattr(client, "port", 0) or 0
    return by_port(int(port))
