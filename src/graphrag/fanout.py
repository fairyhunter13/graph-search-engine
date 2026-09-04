"""One federated read spread over a few threads, without losing the early stop.

coderag hit this defect first and fixed it at `conns.fanout`. The shape differs
in one way that decides this module: coderag caches a handle per thread and a
reaper closes it later, so its pool needs a session and a lock. Here a store is
opened, read and closed inside the one call, so there is no handle for a second
thread to reach and nothing to guard.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor

from . import config

_pool: ThreadPoolExecutor | None = None
_pool_lock = threading.Lock()


def pool() -> ThreadPoolExecutor:
    """One executor for the process, built once and never replaced.

    A pool per call would build and join four threads on every federated
    question. It would also have to be closed, and the caller of `windowed`
    stops reading part way through on purpose.
    """
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(
                max_workers=max(1, config.FANOUT_WORKERS), thread_name_prefix="graphrag-fanout"
            )
        return _pool


def windowed[T, R](fn: Callable[[T], R], items: Iterable[T]) -> Iterator[R]:
    """Yield `fn(item)` for each item, in the order asked, one window at a time.

    A generator, and not a list, because the caller stops as soon as it holds
    enough hits. One `map` over the whole list opens every store whatever the
    answer is, and a common name is answered by the first store. So a full map
    would cost more than the plain loop it replaces on the common case. A
    window of `FANOUT_WORKERS` wastes at most `FANOUT_WORKERS - 1` opens when
    the caller stops.

    In order, and never as the threads finish. `federation.expand` puts the
    root first and the caller keeps the first `limit` hits, so an order set by
    disk timing would change which project answers.
    """
    items = list(items)
    size = max(1, config.FANOUT_WORKERS)
    if len(items) < 2 or size < 2:
        for item in items:
            yield fn(item)
        return
    live = pool()
    for start in range(0, len(items), size):
        yield from live.map(fn, items[start : start + size])
