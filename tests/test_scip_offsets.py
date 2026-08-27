"""S-06. The encoding table, graded where it is wrong and nothing else catches it.

A column is a byte count on `scip-go` and a UTF-16 code-unit count on
`scip-python`, and neither declares which. So the same identifier in the same
file carries two different columns, and both have to land on one byte range or
the overlay writes an edge onto the wrong node.
"""

from __future__ import annotations

import pytest

from graphrag.scip import offsets
from graphrag.scip.read import UTF8, UTF16, UTF32, Range

# `Café` sits at line 4. `class ` is six ASCII characters, so it starts at
# column 6 under every encoding, and it ends at 10 in UTF-16 and 11 in UTF-8.
SRC = "def alpha():\n    return 1\n\n\nclass Café:\n    def beta(self):\n        return alpha()\n"
NAME_BYTES = (34, 39)


def test_non_ascii_ranges_agree():
    """T-18. Two indexers, two column counts, one byte range."""
    table = offsets.Offsets.build(SRC)
    python = table.span(Range(4, 6, 4, 10), offsets.encoding_for("scip-python"))
    go = table.span(Range(4, 6, 4, 11), offsets.encoding_for("scip-go"))
    assert python == go == NAME_BYTES

    # An ASCII name is the control. It agrees under both, so a passing pair
    # above is the non-ASCII case and never the table being ignored.
    ascii_span = Range(0, 4, 0, 9)
    assert table.span(ascii_span, UTF8) == table.span(ascii_span, UTF16) == (4, 9)


def test_a_declared_encoding_beats_the_table():
    """The field is authoritative where an indexer sets it, which three do."""
    assert offsets.encoding_for("scip-python") == UTF16
    assert offsets.encoding_for("scip-python", UTF8) == UTF8
    assert offsets.encoding_for("scip-go") == UTF8


def test_an_unknown_tool_is_an_error_and_never_a_guess():
    """Unset does not mean one thing, so a name off the table cannot be defaulted."""
    with pytest.raises(offsets.EncodingError) as caught:
        offsets.encoding_for("scip-cobol")
    assert "scip-cobol" in str(caught.value)
    assert "scip-go" in str(caught.value)


def test_an_astral_character_counts_as_two_utf16_units():
    """The surrogate pair is the half of UTF-16 a naive character count misses."""
    table = offsets.Offsets.build("x = '\U0001f600' + y\n")
    # The emoji is one code point, two UTF-16 units and four bytes, so the
    # closing quote after it is unit 7, character 6 and byte 9.
    assert table.byte(0, 7, UTF16) == table.byte(0, 6, UTF32) == 9


def test_a_line_splits_on_newline_alone():
    """`str.splitlines()` also splits on `\x0b`, and every later line then shifts."""
    table = offsets.Offsets.build("a = 1\x0bb = 2\nc = 3\n")
    assert table.byte(1, 0, UTF8) == 12


def test_an_end_before_its_start_collapses_rather_than_inverting():
    """An empty range is legal, so the span is clamped and never negative."""
    table = offsets.Offsets.build(SRC)
    assert table.span(Range(0, 9, 0, 4), UTF8) == (9, 9)
