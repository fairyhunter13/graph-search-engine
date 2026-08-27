"""The registry row, as a dataclass.

Its own module because `registry.py` is the locking discipline and this is the
record shape. A new-file line ceiling forced the split, and the split is right:
the store, the CLI and the reach hook all read a row without taking a lock.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ProjectEntry:
    """One row. `roots` is which other projects claim this one as a member."""

    path: str
    enabled: bool = True
    direct: bool = False
    roots: list[str] = field(default_factory=list)
    last_indexed: float = 0.0
    last_error: str | None = None

    def to_json(self) -> dict:
        return {
            "enabled": self.enabled,
            "direct": self.direct,
            "roots": sorted(self.roots),
            "last_indexed": self.last_indexed,
            "last_error": self.last_error,
        }

    @classmethod
    def from_json(cls, path: str, row: dict) -> ProjectEntry:
        return cls(
            path=path,
            enabled=bool(row.get("enabled", True)),
            direct=bool(row.get("direct", False)),
            roots=list(row.get("roots", [])),
            last_indexed=float(row.get("last_indexed", 0.0)),
            last_error=row.get("last_error"),
        )
