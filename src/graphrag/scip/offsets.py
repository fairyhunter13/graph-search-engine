"""Every SCIP range, normalized to an absolute UTF-8 byte offset.

`position_encoding` is unset on most indexers, and unset does not mean one
thing. `scip-go` leaves it 0 and emits UTF-8 bytes; `scip-python` and
`scip-typescript` leave it 0 and emit UTF-16, because both are TypeScript
programs counting `string` indices. `scip-dotnet` and `scip-ruby` vendor a
proto that has no such field at all, so they cannot declare one.

So the fallback is keyed on `tool_info.name`, never on the field, and an
unknown tool name is an error. A guess here is silent: every offset lands one
or two bytes out on any line holding a non-ASCII character, and the symptom is
a node whose byte range names the middle of an identifier.
"""

from __future__ import annotations

from dataclasses import dataclass

from .read import UNSPECIFIED, UTF8, UTF16, UTF32, Range

# Measured 2026-08-27 for the first three. The rest follow their host language,
# because these indexers count the column with their own runtime's string type:
# a JVM, .NET or Dart `String` is UTF-16, and a C++ one is bytes.
_DEFAULT_ENCODING: dict[str, int] = {
    "scip-go": UTF8,
    "scip-python": UTF16,
    "scip-typescript": UTF16,
    "scip-java": UTF16,
    "scip-kotlin": UTF16,
    "scip-dotnet": UTF16,
    "scip-dart": UTF16,
    "scip-clang": UTF8,
    "scip-ruby": UTF8,
    "scip-php": UTF8,
    "rust-analyzer": UTF16,
}


class EncodingError(ValueError):
    """A tool whose column units this table cannot name."""


def encoding_for(tool_name: str, declared: int = UNSPECIFIED) -> int:
    """What the columns in this index actually count.

    A declared encoding wins, because the indexer that sets the field is the
    one that knows. Only `rust-analyzer`, `scip-php` and `debian-lsp` set it.
    """
    if declared != UNSPECIFIED:
        return declared
    got = _DEFAULT_ENCODING.get(tool_name)
    if got is None:
        raise EncodingError(
            f"{tool_name!r} declares no position_encoding and this table does not "
            f"know what its columns count. Known tools: {', '.join(sorted(_DEFAULT_ENCODING))}"
        )
    return got


def _byte_in_line(line: str, character: int, encoding: int) -> int:
    """A column, in this encoding's units, as a byte offset into the line."""
    if character <= 0:
        return 0
    if encoding == UTF8:
        return min(character, len(line.encode()))
    if encoding == UTF32:
        return len(line[:character].encode())
    units = 0
    for i, char in enumerate(line):
        if units >= character:
            return len(line[:i].encode())
        units += 2 if ord(char) > 0xFFFF else 1
    return len(line.encode())


@dataclass(slots=True)
class Offsets:
    """One file's line table, built once and asked many times."""

    lines: list[str]
    starts: list[int]

    @classmethod
    def build(cls, text: str) -> Offsets:
        """Split on `\n` and nothing else.

        `str.splitlines()` also splits on `\v`, `\f`, `\x85` and the two
        Unicode separators, and a file holding one of those would shift every
        line after it with no error anywhere.
        """
        lines = text.split("\n")
        starts: list[int] = []
        offset = 0
        for line in lines:
            starts.append(offset)
            offset += len(line.encode()) + 1
        return cls(lines=lines, starts=starts)

    def byte(self, line: int, character: int, encoding: int) -> int:
        if line < 0:
            return 0
        if line >= len(self.lines):
            return self.starts[-1] + len(self.lines[-1].encode())
        return self.starts[line] + _byte_in_line(self.lines[line], character, encoding)

    def span(self, span: Range, encoding: int) -> tuple[int, int]:
        """One occurrence range as absolute UTF-8 bytes, half-open."""
        start = self.byte(span.start_line, span.start_char, encoding)
        end = self.byte(span.end_line, span.end_char, encoding)
        return (start, max(start, end))
