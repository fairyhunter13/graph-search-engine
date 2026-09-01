"""What is a source file, what language it is, and what is never indexed.

`indexable()` is shared by the watcher and the indexer. A watcher that decides
differently wakes the indexer for files it will then refuse, forever.

The language name is the extension's answer and never the index's. Neither
scip-python nor scip-typescript sets `Document.language`, so a reader that
trusts that field gets an empty string and files everything under one key.
"""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

# Extension to the `tree-sitter-language-pack` name. The pack's spelling is the
# key everywhere downstream, so `c_sharp` and `csharp` are not interchangeable.
EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".swift": "swift",
    ".lua": "lua",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".ml": "ocaml",
    ".dart": "dart",
    ".jl": "julia",
    ".r": "r",
    ".pl": "perl",
    ".hs": "haskell",
    ".zig": "zig",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".vue": "vue",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".tf": "terraform",
    ".hcl": "hcl",
    ".proto": "proto",
}

# Directory names never descended into. A vendored tree is somebody else's
# graph, and indexing it makes every symbol in it a candidate for every call.
SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "vendor",
        "target",
        "build",
        "dist",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".next",
        ".nuxt",
        "site-packages",
        ".terraform",
    }
)

# A file over this is machine-written, and a generated bundle is one node with
# ten thousand edges that resolve nothing. 2 MB, measured against the largest
# hand-written file in the fleet at about 180 KB.
MAX_FILE_BYTES = 2 * 1024 * 1024

# zoekt's `TrigramMax`. A document holding more distinct 3-byte sequences than
# this is machine-written, whatever it is named: a bundle called `app.js` walks
# straight past a `.min.js` suffix test.
MAX_DISTINCT_TRIGRAMS = 20_000

# Only a file this large is read for the test above. Measured 2026-09-01: every
# hand-written source file in this repo holds under 2,800 distinct trigrams, and
# the scan costs about 0.19 ms per KB, so running it on a whole tree would cost
# more than the parse it saves.
CONTENT_SCAN_BYTES = 64 * 1024

# Roots that are somebody's whole disk rather than a project. Indexing one of
# these enrols every repo on the machine under a single graph, and the registry
# then holds a row nothing can meaningfully re-index.
_FORBIDDEN_ROOTS: frozenset[Path] = frozenset(
    {
        Path("/"),
        Path.home(),
        Path("/usr"),
        Path("/etc"),
        Path("/var"),
        Path("/opt"),
        Path("/tmp"),
    }
)


def language_of(path: Path | str) -> str:
    """The pack's language name, or an empty string.

    An empty string is not a refusal. A file with no grammar still gets a row
    and still carries import edges where a query exists for it.
    """
    return EXTENSIONS.get(Path(path).suffix.lower(), "")


def is_forbidden_root(path: Path | str) -> bool:
    """Whether this path is a home or a system directory rather than a project."""
    resolved = Path(path).expanduser().resolve()
    return resolved in _FORBIDDEN_ROOTS


def skipped_dir(name: str) -> bool:
    return name in SKIP_DIRS or (name.startswith(".") and name not in (".github",))


def matches_any(rel: str, patterns) -> bool:
    """fnmatch a relative path, with the directory form tried too.

    `fnmatch`'s `*` spans `/`, so `system/*` matches at any depth. That is what
    the config lists assume, and it is why these are not glob(1). The trailing
    slash form is what lets a bare directory pattern match the directory itself.
    """
    return any(fnmatch(rel, pat) or fnmatch(f"{rel}/", pat) for pat in patterns)


def indexable(path: Path, *, size: int | None = None) -> bool:
    """The one predicate. The watcher and the indexer both call this.

    Size is passed in where the caller already has a stat, so a walk of 100k
    files does not stat every one of them twice.
    """
    if not language_of(path):
        return False
    if any(skipped_dir(part) for part in path.parts[:-1]):
        return False
    if size is None:
        try:
            size = path.stat().st_size
        except OSError:
            return False
    return 0 < size <= MAX_FILE_BYTES


def generated(data: bytes) -> bool:
    """Whether this content is machine-written, read from the bytes and not the name.

    Distinct trigrams, which is zoekt's rule. Measured 2026-09-01 over the
    `web-tree` tree: six real bundles crossed the cap between 173 KB and
    663 KB in, and `elfinder.full.js` and `shared-ui.js` are pretty-printed, so a
    line-length test passes both. The cap is what separates them.
    """
    seen: set[bytes] = set()
    add = seen.add
    for i in range(len(data) - 2):
        add(data[i : i + 3])
        if len(seen) > MAX_DISTINCT_TRIGRAMS:
            return True
    return False
