"""Protobuf wire format, read with the standard library and nothing else.

SCIP ships no Python binding and none is planned. Generated code would vendor a
file nobody reviews and pin a runtime that has to move with it, and the surface
actually read here is eight messages and twenty fields. The wire format itself
is frozen, so this decoder is the smaller liability. `T-102` grades it against
`protoc --decode`, which is the only evidence that it reads what SCIP wrote.
"""

from __future__ import annotations

from collections.abc import Iterator

VARINT = 0
FIXED64 = 1
LENGTH = 2
FIXED32 = 5

_INT32 = 1 << 32
_INT64 = 1 << 64


def varint(data, i: int) -> tuple[int, int]:
    """One base-128 varint, and the index after it."""
    value = shift = 0
    while True:
        if i >= len(data):
            raise ValueError("a varint runs past the end of the message")
        byte = data[i]
        i += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, i
        shift += 7
        if shift > 63:
            raise ValueError("a varint is longer than 64 bits")


def to_int32(value: int) -> int:
    """A negative int32 travels as a ten-byte two's complement varint."""
    value &= _INT64 - 1
    if value >= _INT64 >> 1:
        value -= _INT64
    if value < -(_INT32 >> 1) or value >= _INT32:
        raise ValueError(f"{value} does not fit an int32")
    return value


def fields(data) -> Iterator[tuple[int, int, object]]:
    """Every field in one message, in wire order.

    A length-delimited payload comes back as a slice of the caller's buffer, so
    a `memoryview` over an mmapped index is never copied to walk it.
    """
    i, end = 0, len(data)
    while i < end:
        key, i = varint(data, i)
        number, kind = key >> 3, key & 7
        if kind == VARINT:
            value, i = varint(data, i)
            yield number, kind, value
        elif kind == LENGTH:
            size, i = varint(data, i)
            if i + size > end:
                raise ValueError("a length-delimited field runs past the end")
            yield number, kind, data[i : i + size]
            i += size
        elif kind == FIXED64:
            yield number, kind, int.from_bytes(bytes(data[i : i + 8]), "little")
            i += 8
        elif kind == FIXED32:
            yield number, kind, int.from_bytes(bytes(data[i : i + 4]), "little")
            i += 4
        else:
            # Groups. Removed from the language before SCIP existed, and there
            # is no length prefix to skip one, so a reader cannot go on.
            raise ValueError(f"wire type {kind} is not readable")


def text(payload) -> str:
    return bytes(payload).decode("utf-8", "replace")


def varints(payload) -> list[int]:
    """A packed repeated varint field."""
    out: list[int] = []
    i = 0
    while i < len(payload):
        value, i = varint(payload, i)
        out.append(value)
    return out


def collect(data) -> dict[int, list[object]]:
    """Every field by number, for a message small enough to hold whole."""
    out: dict[int, list[object]] = {}
    for number, _kind, value in fields(data):
        out.setdefault(number, []).append(value)
    return out
