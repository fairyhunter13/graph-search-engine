"""How a call site's receiver is read, and when it is the caller's own.

Split out of `extract.py` when that module crossed the 300-line ceiling. The
seam is a real one rather than a line count: everything here reads bytes around
an identifier, or a Go declaration's receiver clause, and none of it knows what
a `FileFacts` is. `extract` owns the walk and the dataclasses.

`text` is passed in rather than imported, because the decoder belongs to the
caller that owns the file's bytes.
"""

from __future__ import annotations

# The byte that precedes an identifier in a member call. `expr.method()` is about
# 43% of call sites.
_MEMBER_BYTES = (b".", b">", b":")

# What a receiver name is spelled with. `$` is here for PHP, where `$this` is
# the receiver and dropping the sigil would make it a different name.
_IDENT_BYTES = frozenset(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$")


def member(data: bytes, node) -> tuple[bool, str]:
    """The separator before an identifier, and the receiver that precedes it.

    The receiver is what tells `registry.load()` from `yaml.load()`. Discarding
    it made the two one name, and `D-18` measured what that costs.
    """
    i = node.start_byte - 1
    while i >= 0 and data[i : i + 1].isspace():
        i -= 1
    if i < 0 or data[i : i + 1] not in _MEMBER_BYTES:
        return False, ""
    # `->` and `::` are two bytes, and the receiver sits before both of them.
    if data[i : i + 1] in (b">", b":") and i > 0 and data[i - 1 : i] in (b"-", b":"):
        i -= 1
    i -= 1
    while i >= 0 and data[i : i + 1].isspace():
        i -= 1
    end = i + 1
    while i >= 0 and data[i] in _IDENT_BYTES:
        i -= 1
    return True, data[i + 1 : end].decode("utf-8", "replace")


def go_receiver(data: bytes, whole) -> str:
    """The name a Go method declaration binds its receiver to, or "".

    `func (s *Service) Handle()` binds `s`, and Go requires every method of
    `Service` to live in that package. So a call on `s` inside `Handle` is
    `self` under an arbitrary name, which is what `Reference.receiver_self`
    records and what lets `SAME_PACKAGE` score the pool.

    Every step is guarded. tree-sitter returns `None` for a field that is not
    there, and a receiver that cannot be read is "" rather than a guess.
    """
    if whole.type != "method_declaration":
        return ""
    clause = whole.child_by_field_name("receiver")
    if clause is None:
        return ""
    for child in clause.named_children:
        if child.type != "parameter_declaration":
            continue
        name = child.child_by_field_name("name")
        return decode(data, name) if name is not None else ""
    return ""


def decode(data: bytes, node) -> str:
    return data[node.start_byte : node.end_byte].decode("utf-8", "replace")


def is_self(definitions, scope: int | None, receiver: str) -> bool:
    """Does `receiver` name the receiver the enclosing method binds?

    The walk is up the parent chain and not the innermost definition alone: a
    closure inside a method is the innermost definition and binds no receiver
    of its own, while the call inside it still says `s`.
    """
    cursor, seen = scope, set()
    while cursor is not None and cursor not in seen:
        seen.add(cursor)
        holder = definitions[cursor].receiver
        if holder:
            return holder == receiver
        cursor = definitions[cursor].parent
    return False
