"""SCIP index reading, one `Document` at a time.

The whole index is never materialized. A `scip-typescript` run over a large
tree is hundreds of megabytes, and a reader that parses it whole holds every
document to use one. The file is mmapped and the top-level walk yields each
document payload as a slice.

Field numbers come from `scip.proto` at tag `v0.9.0`, sha256
`04cb20f2b8be73f6c0376b5b3e84c3ae20ebaff0ad3d23ba2d16f866b395ed7d`. `main` has
moved since, so the pin is the tag and not the branch.
"""

from __future__ import annotations

import mmap
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from . import wire

# PositionEncoding. 0 is `Unspecified`, and unspecified does not mean one
# thing: `offsets.py` keys the fallback on the tool name instead.
UNSPECIFIED, UTF8, UTF16, UTF32 = 0, 1, 2, 3

DEFINITION = 0x1


@dataclass(frozen=True, slots=True)
class Range:
    """Half-open, 0-based, in whatever units the document's encoding names."""

    start_line: int
    start_char: int
    end_line: int
    end_char: int


@dataclass(slots=True)
class Relationship:
    symbol: str
    is_reference: bool = False
    is_implementation: bool = False
    is_type_definition: bool = False
    is_definition: bool = False


@dataclass(slots=True)
class SymbolInfo:
    symbol: str
    kind: int = 0
    display_name: str = ""
    documentation: list[str] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    enclosing_symbol: str = ""


@dataclass(slots=True)
class Occurrence:
    symbol: str = ""
    roles: int = 0
    span: Range | None = None

    @property
    def is_definition(self) -> bool:
        return bool(self.roles & DEFINITION)


@dataclass(slots=True)
class Document:
    relative_path: str = ""
    language: str = ""
    encoding: int = UNSPECIFIED
    text: str = ""
    occurrences: list[Occurrence] = field(default_factory=list)
    symbols: list[SymbolInfo] = field(default_factory=list)


@dataclass(slots=True)
class Metadata:
    tool_name: str = ""
    tool_version: str = ""
    project_root: str = ""


def _typed_range(payload, multiline: bool) -> Range:
    got = wire.collect(payload)

    def one(number: int) -> int:
        values = got.get(number)
        return wire.to_int32(values[0]) if values else 0

    if multiline:
        return Range(one(1), one(2), one(3), one(4))
    line = one(1)
    return Range(line, one(2), line, one(3))


def _deprecated_range(values: list[int]) -> Range | None:
    """Three elements or four, and anything else is not a range."""
    got = [wire.to_int32(v) for v in values]
    if len(got) == 3:
        return Range(got[0], got[1], got[0], got[2])
    if len(got) == 4:
        return Range(got[0], got[1], got[2], got[3])
    return None


def _occurrence(payload) -> Occurrence:
    """The three range shapes, and `typed_range` wins where two are set."""
    out = Occurrence()
    flat: list[int] = []
    typed: Range | None = None
    for number, kind, value in wire.fields(payload):
        if number == 1:
            flat.extend(wire.varints(value) if kind == wire.LENGTH else [value])
        elif number == 2:
            out.symbol = wire.text(value)
        elif number == 3:
            out.roles = wire.to_int32(value)
        elif number in (8, 9):
            typed = _typed_range(value, multiline=number == 9)
    out.span = typed if typed is not None else _deprecated_range(flat)
    return out


def _relationship(payload) -> Relationship:
    out = Relationship(symbol="")
    for number, _kind, value in wire.fields(payload):
        if number == 1:
            out.symbol = wire.text(value)
        elif number == 2:
            out.is_reference = bool(value)
        elif number == 3:
            out.is_implementation = bool(value)
        elif number == 4:
            out.is_type_definition = bool(value)
        elif number == 5:
            out.is_definition = bool(value)
    return out


def _symbol_info(payload) -> SymbolInfo:
    out = SymbolInfo(symbol="")
    for number, _kind, value in wire.fields(payload):
        if number == 1:
            out.symbol = wire.text(value)
        elif number == 3:
            out.documentation.append(wire.text(value))
        elif number == 4:
            out.relationships.append(_relationship(value))
        elif number == 5:
            out.kind = wire.to_int32(value)
        elif number == 6:
            out.display_name = wire.text(value)
        elif number == 8:
            out.enclosing_symbol = wire.text(value)
    return out


def _document(payload) -> Document:
    out = Document()
    for number, _kind, value in wire.fields(payload):
        if number == 1:
            out.relative_path = wire.text(value)
        elif number == 2:
            out.occurrences.append(_occurrence(value))
        elif number == 3:
            out.symbols.append(_symbol_info(value))
        elif number == 4:
            out.language = wire.text(value)
        elif number == 5:
            out.text = wire.text(value)
        elif number == 6:
            out.encoding = wire.to_int32(value)
    return out


def _metadata(payload) -> Metadata:
    out = Metadata()
    for number, _kind, value in wire.fields(payload):
        if number == 2:
            for inner, _k, tool in wire.fields(value):
                if inner == 1:
                    out.tool_name = wire.text(tool)
                elif inner == 2:
                    out.tool_version = wire.text(tool)
        elif number == 3:
            out.project_root = wire.text(value)
    return out


@contextmanager
def _mapped(path: Path | str):
    path = Path(path)
    if path.stat().st_size == 0:
        raise ValueError(f"{path} is empty, so it is not a SCIP index")
    with open(path, "rb") as handle:
        # The mmap itself, never a `memoryview` over it. A view exported to a
        # generator that is abandoned mid-walk keeps the export alive, and the
        # close then raises where the caller merely stopped reading.
        buffer = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            yield buffer
        finally:
            buffer.close()


def metadata(path: Path | str) -> Metadata:
    """The tool that wrote this index. The encoding table is keyed on its name."""
    with _mapped(path) as data:
        for number, _kind, value in wire.fields(data):
            if number == 1:
                return _metadata(value)
    return Metadata()


def documents(path: Path | str) -> Iterator[Document]:
    """Every document, one at a time. The index is never held whole."""
    with _mapped(path) as data:
        for number, _kind, value in wire.fields(data):
            if number == 2:
                yield _document(value)
