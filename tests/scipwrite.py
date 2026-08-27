"""A minimal SCIP writer, so a test can hand the reader a real index.

Not a mock. It emits protobuf wire bytes that `protoc --decode` reads against
the real `scip.proto`, and `T-102` is that cross-check. A test that fed the
reader a Python object would prove only that the reader agrees with itself.
"""

from __future__ import annotations

DEPRECATED, SINGLE, MULTI = "deprecated", "single", "multi"


def _varint(value: int) -> bytes:
    if value < 0:
        value += 1 << 64
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def _tag(number: int, kind: int) -> bytes:
    return _varint((number << 3) | kind)


def _var(number: int, value: int) -> bytes:
    return _tag(number, 0) + _varint(value)


def _bytes(number: int, payload: bytes) -> bytes:
    return _tag(number, 2) + _varint(len(payload)) + payload


def _str(number: int, value: str) -> bytes:
    return _bytes(number, value.encode())


def _packed(number: int, values) -> bytes:
    return _bytes(number, b"".join(_varint(v) for v in values))


def occurrence(symbol: str, *, roles: int = 0, span=None, shape: str = DEPRECATED) -> bytes:
    out = _str(2, symbol)
    if roles:
        out += _var(3, roles)
    if span is None:
        return out
    start_line, start_char, end_line, end_char = span
    if shape == SINGLE:
        return out + _bytes(8, _var(1, start_line) + _var(2, start_char) + _var(3, end_char))
    if shape == MULTI:
        inner = _var(1, start_line) + _var(2, start_char) + _var(3, end_line) + _var(4, end_char)
        return out + _bytes(9, inner)
    flat = (
        [start_line, start_char, end_char]
        if start_line == end_line
        else [start_line, start_char, end_line, end_char]
    )
    return out + _packed(1, flat)


def relationship(symbol: str, *, implementation: bool = False) -> bytes:
    return _str(1, symbol) + (_var(3, 1) if implementation else b"")


def symbol_info(symbol: str, *, kind: int = 0, documentation=(), relationships=()) -> bytes:
    out = _str(1, symbol)
    for line in documentation:
        out += _str(3, line)
    for rel in relationships:
        out += _bytes(4, rel)
    if kind:
        out += _var(5, kind)
    return out


def document(path: str, *, occurrences=(), symbols=(), text: str = "", encoding: int = 0) -> bytes:
    out = _str(1, path)
    for one in occurrences:
        out += _bytes(2, one)
    for one in symbols:
        out += _bytes(3, one)
    if text:
        out += _str(5, text)
    if encoding:
        out += _var(6, encoding)
    return out


def index(tool: str, documents=(), *, version: str = "0.1", project_root: str = "") -> bytes:
    metadata = _bytes(2, _str(1, tool) + _str(2, version))
    if project_root:
        metadata += _str(3, project_root)
    out = _bytes(1, metadata)
    for one in documents:
        out += _bytes(2, one)
    return out


def write(path, tool: str, documents=(), **kwargs) -> None:
    path.write_bytes(index(tool, documents, **kwargs))
