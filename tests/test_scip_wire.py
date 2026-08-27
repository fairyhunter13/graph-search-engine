"""The stdlib protobuf decoder, graded against `protoc`.

`T-102` is the only evidence that this reader reads what SCIP writes. Every
other SCIP test here feeds the reader bytes this repo also encoded, so on its
own that pair would prove only that the two agree with each other.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import scipwrite as w
from graphrag.scip import read, wire

PROTO = Path(__file__).resolve().parent / "fixtures" / "scip" / "scip.proto"

SAMPLE = w.index(
    "scip-python",
    [
        w.document(
            "pkg/a.py",
            occurrences=[
                w.occurrence("scip-python python . . alpha().", roles=1, span=(0, 4, 0, 9)),
                w.occurrence("scip-python python . . beta().", span=(6, 15, 6, 20), shape=w.SINGLE),
            ],
            symbols=[
                w.symbol_info("scip-python python . . alpha().", kind=17, documentation=["d"])
            ],
        )
    ],
    project_root="file:///tmp/pkg",
)


def test_a_varint_round_trips_through_both_halves():
    """`T-102`. The negative case is the one a hand-rolled reader gets wrong."""
    for value in (0, 1, 127, 128, 300, 2**31 - 1):
        assert wire.varint(w._varint(value), 0) == (value, len(w._varint(value)))
    assert wire.to_int32(0xFFFFFFFFFFFFFFFF) == -1
    with pytest.raises(ValueError):
        wire.varint(b"\x80", 0)


def test_a_group_wire_type_is_refused_rather_than_skipped():
    """Wire type 3 carries no length, so a reader cannot step over it."""
    with pytest.raises(ValueError, match="not readable"):
        list(wire.fields(b"\x0b"))


def test_the_decoder_agrees_with_protoc(tmp_path):
    """`T-102`. `protoc` reads the same bytes against the real `scip.proto`."""
    if shutil.which("protoc") is None:
        pytest.skip("no protoc, so the decoder would only be graded against itself")
    path = tmp_path / "index.scip"
    path.write_bytes(SAMPLE)
    got = subprocess.run(
        ["protoc", f"--proto_path={PROTO.parent}", "--decode=scip.Index", PROTO.name],
        input=SAMPLE,
        capture_output=True,
        check=True,
    ).stdout.decode()

    assert "scip-python" in got
    assert "pkg/a.py" in got
    assert read.metadata(path).tool_name == "scip-python"
    documents = list(read.documents(path))
    assert [d.relative_path for d in documents] == ["pkg/a.py"]
    assert got.count("occurrences {") == len(documents[0].occurrences)
    assert got.count("symbols {") == len(documents[0].symbols)
    assert documents[0].symbols[0].kind == 17
    assert documents[0].symbols[0].documentation == ["d"]
