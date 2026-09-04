"""The three properties that make a threaded federated walk correct.

`find_symbol` walked the root plus every member one store at a time. Threading
it is only safe if the answer does not change, and two of the arms below fail
against the two obvious ways to get it wrong: yield as the threads finish, or
map over the whole list at once.
"""

from __future__ import annotations

import threading
import time

import pytest

from graphrag import config, fanout, federation, index, tools

SRC = {"a.py": "def alpha():\n    return 1\n"}


@pytest.fixture
def pooled(monkeypatch):
    """Four workers, and a pool built fresh for this test.

    The pool takes its worker count once, at first use. A later change to
    `FANOUT_WORKERS` moves the window and leaves the threads where they were,
    so a test that changes the count has to drop the pool with it.
    """
    fanout._pool = None
    monkeypatch.setattr(config, "FANOUT_WORKERS", 4)
    yield
    fanout._pool = None


def test_results_come_back_in_the_order_asked(pooled):
    """The negative arm for a fan-out that yields as the threads finish.

    `federation.expand` puts the root first and the caller keeps the first
    `limit` hits. So an order set by disk timing changes which project answers,
    and the answer stops being a function of the question.
    """
    finished = []

    def slow(n: int) -> int:
        # Item 0 is the slowest, so completion order is the reverse of the ask.
        time.sleep(0.05 * (4 - n))
        finished.append(n)
        return n

    assert list(fanout.windowed(slow, [0, 1, 2, 3])) == [0, 1, 2, 3]
    # Without this line a plain sequential loop passes the arm above, and the
    # test proves nothing about the threading it was written for.
    assert finished != [0, 1, 2, 3], finished


def test_a_caller_that_stops_early_reads_one_window(pooled):
    """The negative arm for one `map` over the whole list.

    A common name is answered by the first store. A map over 383 members opens
    383 stores whatever the answer is, so it would cost more than the plain
    loop it replaces on the common case.
    """
    opened: list[int] = []
    lock = threading.Lock()

    def read(n: int) -> int:
        with lock:
            opened.append(n)
        return n

    stream = fanout.windowed(read, list(range(40)))
    assert next(stream) == 0
    stream.close()
    # Exactly the window, and not a bound loose enough to hide a full map: the
    # broken version opens all 40.
    assert len(opened) <= 4, opened


def test_one_worker_restores_the_plain_loop(monkeypatch):
    """`FANOUT_WORKERS=1` is the arm a regression is measured against.

    It has to be the sequential loop and not a pool of one, because a pool of
    one still moves the work onto another thread and changes what a profile of
    the caller reads.
    """
    fanout._pool = None
    monkeypatch.setattr(config, "FANOUT_WORKERS", 1)
    ran_on = []

    def note(n: int) -> int:
        ran_on.append(threading.current_thread().name)
        return n

    assert list(fanout.windowed(note, [1, 2, 3])) == [1, 2, 3]
    assert set(ran_on) == {threading.current_thread().name}, ran_on


def test_a_member_with_no_graph_is_named_and_not_raised(repo, pooled):
    """A `LookupError` on a worker must not end the walk at the first member.

    The sequential loop caught it per project and carried on. Crossing a pool
    it would surface at the consuming loop instead, and every member after the
    unindexed one would go unread.
    """
    member = repo("member", SRC)
    root = repo("root", SRC)
    (root / ".graphrag.yaml").write_text(f"members: ['{member}']\n")
    # Only the root is indexed. The member is a project nobody has passed.
    index.index_once(root)
    assert federation.expand(root) == [root, member]

    answer = tools.find_symbol(name="alpha", root=str(root))
    assert [hit["project"] for hit in answer["results"]] == [str(root)], answer
    assert any(str(member) in gap for gap in answer["gaps"]), answer
