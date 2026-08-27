"""A short id, carried through one request and echoed in every error it raises.

A caller who reads "the graph could not be opened" has nothing to search a
ledger with. A caller who reads the same sentence with `a1b2c3d4` after it can
find the row that recorded what happened, which is the whole point of writing
rows nobody reads back as state.
"""

from __future__ import annotations

import contextlib
import secrets
from collections.abc import Generator
from contextvars import ContextVar

# A context variable, not a thread local. The daemon serves on an event loop, so
# two requests share a thread and a thread local would hand one the other's id.
_current: ContextVar[str] = ContextVar("graphrag_trace", default="")


def new() -> str:
    """Short enough for a caller to quote back out of an error message."""
    return secrets.token_hex(4)


def current() -> str:
    return _current.get()


@contextlib.contextmanager
def span(trace_id: str = "") -> Generator[str]:
    token = _current.set(trace_id or new())
    try:
        yield _current.get()
    finally:
        _current.reset(token)


def stamp(message: str) -> str:
    """The error text with its trace id, or unchanged outside a span."""
    trace_id = current()
    return f"{message} [trace {trace_id}]" if trace_id else message
