"""The three occurrence range shapes, and what is dropped rather than guessed.

v0.8.0 deprecated `repeated int32 range` for `oneof typed_range`, and scip-java
v0.13 emits only the new form. A reader that handles the deprecated field alone
gets zero ranges from scip-java, with no error anywhere.
"""

from __future__ import annotations

import scipwrite as w
from graphrag.scip import read

SPAN = (4, 6, 4, 10)


def _one(tmp_path, occurrence) -> read.Occurrence:
    path = tmp_path / "index.scip"
    w.write(path, "scip-go", [w.document("a.go", occurrences=[occurrence])])
    return next(read.documents(path)).occurrences[0]


def test_all_three_range_shapes_yield_one_span(tmp_path):
    """`T-103`. Three encodings of one range, and one answer."""
    got = [
        _one(tmp_path, w.occurrence("s", span=SPAN, shape=shape)).span
        for shape in (w.DEPRECATED, w.SINGLE, w.MULTI)
    ]
    assert got == [read.Range(*SPAN)] * 3


def test_a_multi_line_deprecated_range_keeps_its_end_line(tmp_path):
    """The four-element form. Three elements infer the end line, four state it."""
    assert _one(tmp_path, w.occurrence("s", span=(2, 1, 5, 3))).span == read.Range(2, 1, 5, 3)


def test_the_typed_range_wins_where_both_are_set(tmp_path):
    """The proto says so, and an index in transition carries both."""
    typed = w._bytes(8, w._var(1, SPAN[0]) + w._var(2, SPAN[1]) + w._var(3, SPAN[3]))
    both = w.occurrence("s", span=(9, 9, 9, 9)) + typed
    assert _one(tmp_path, both).span == read.Range(*SPAN)


def test_an_occurrence_with_no_range_survives_as_no_span(tmp_path):
    """They exist in the wild, so the reader reports one rather than inventing."""
    assert _one(tmp_path, w.occurrence("s")).span is None


def test_a_two_element_range_is_not_a_range(tmp_path):
    """Three or four elements. Anything else names no span, and is dropped."""
    raw = w.occurrence("s") + w._packed(1, [1, 2])
    assert _one(tmp_path, raw).span is None


def test_the_definition_role_is_one_bit_of_many(tmp_path):
    """`Definition` is `0x1`, and an occurrence carrying `Import` too is still one."""
    got = _one(tmp_path, w.occurrence("s", roles=0x1 | 0x2, span=SPAN))
    assert got.is_definition
    assert not _one(tmp_path, w.occurrence("s", roles=0x8, span=SPAN)).is_definition
