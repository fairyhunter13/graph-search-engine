"""Declared members, one level of expansion, and the workspace they scope.

Real directories and a real registry file. A member here is a line in a config,
so every case writes the config the operator would write.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from graphrag import federation, peers, registry, scope

SRC = {"a.py": "def alpha():\n    return 1\n"}


@pytest.fixture
def workspace(repo):
    """A root declaring one member, and a member declaring one of its own."""
    far = repo("far", SRC)
    near = repo("near", SRC)
    root = repo("root", SRC)
    (near / ".graphrag.yaml").write_text(f"members: ['{far}']\n")
    (root / ".graphrag.yaml").write_text(f"members: ['{near}']\n")
    return root, near, far


def test_federation_expands_one_level(workspace):
    """`T-65`: a member's members belong to the member, never to the root."""
    root, near, far = workspace
    assert federation.members_of(root) == [near]
    assert federation.expand(root) == [root, near]
    # The far repo is reachable from `near` and from nowhere else.
    assert federation.members_of(near) == [far]
    assert far not in federation.expand(root)


def test_a_member_is_an_indirect_claim(workspace):
    """Releasing the root releases the member, and a direct row survives it."""
    root, near, _ = workspace
    assert federation.register(root) == [near]
    entry = registry.get(near)
    assert entry is not None
    assert entry.direct is False
    assert entry.roots == [str(root)]

    assert federation.unregister(root) == [near]
    assert registry.get(near) is None
    assert registry.get(root) is not None


def test_a_member_dropped_from_the_config_loses_the_claim(workspace):
    """The declaration is the truth, so a sweep follows it in both directions."""
    root, near, _ = workspace
    federation.register(root)
    (root / ".graphrag.yaml").write_text("members: []\n")

    added, removed = federation.sweep(root)
    assert added == []
    assert removed == [near]
    assert registry.get(near) is None


def test_an_absent_member_is_dropped_rather_than_raised(repo):
    """A member on an unmounted disk is absent, not a config that cannot parse."""
    root = repo("lonely", SRC)
    (root / ".graphrag.yaml").write_text(f"members: ['{root.parent}/never-existed']\n")
    assert federation.members_of(root) == []
    assert federation.expand(root) == [root]


def test_a_member_naming_itself_is_ignored(repo):
    """A root federating itself would claim its own row on its own behalf."""
    root = repo("selfish", SRC)
    (root / ".graphrag.yaml").write_text(f"members: ['{root}', '.']\n")
    assert federation.members_of(root) == []


def test_a_config_that_cannot_be_obeyed_federates_nothing(repo):
    """A half-read member list is worse than none, so the answer is none."""
    root = repo("broken", SRC)
    (root / ".graphrag.yaml").write_text("membres: []\n")
    assert federation.members_of(root) == []


def test_scope_reaches_a_member_and_stops_there(workspace):
    """Containment covers the root and its members, and names the set on a miss."""
    root, near, far = workspace
    assert scope.contains(root, root / "a.py")
    assert not scope.contains(root, near / "a.py")
    assert scope.within(root, near / "a.py")
    assert not scope.within(root, far / "a.py")

    assert scope.refuse(root, near / "a.py") == ""
    said = scope.refuse(root, far / "a.py")
    assert str(far) in said
    assert str(near) in said, "the refusal must name what is reachable"


def test_the_deepest_enrolled_root_owns_a_path(repo):
    """A project inside another is the more specific answer for its own files."""
    outer = repo("outer", SRC)
    inner = outer / "vendor" / "inner"
    inner.mkdir(parents=True)
    (inner / "b.py").write_text("def beta():\n    return 2\n")
    registry.claim(outer, direct=True)
    registry.claim(inner, direct=True)

    assert scope.owner(inner / "b.py") == inner
    assert scope.owner(outer / "a.py") == outer
    assert scope.owner(outer.parent) is None


def test_this_process_is_named_by_its_own_source_port():
    """A peer is looked up, never guessed, and an unowned port says so."""
    listener = socket.create_server(("127.0.0.1", 0))
    client = socket.create_connection(listener.getsockname())
    try:
        comm = Path("/proc/self/comm").read_text().strip()
        assert peers.by_port(client.getsockname()[1]) == f"{os.getpid()}:{comm}"
    finally:
        client.close()
        listener.close()
    # Port 0 is never a source port, so it resolves without touching `/proc`.
    assert peers.by_port(0) == peers.UNKNOWN
