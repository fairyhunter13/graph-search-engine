"""Vue and Svelte: extract the one real script a single-file component wraps.

No grammar named "vue" or "svelte" parses a component's markup and script
together. Both wrap a real script in `<script>` tags, so this project
extracts what it finds there and calls the rest a gap. A template expression
-- `{{ foo() }}`, `{foo()}` -- is not reached.

This module takes no dependency on `extract.py` at runtime, and calls back
into it through the `parse` parameter instead, because `extract.extract`
dispatches here for `vue` and `svelte` and an import in the other direction
would be circular.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .extract import FileFacts

_SCRIPT_RE = re.compile(r"(?is)<script\b([^>]*)>(.*?)</script>")
_SCRIPT_TS_RE = re.compile(r'lang\s*=\s*["\']?(ts|tsx)\b', re.IGNORECASE)


def embedded_script(
    path_lang: str, text: str, parse: Callable[[str, str], "FileFacts"]
) -> "FileFacts":
    """Every `<script>` block's facts, on the outer file's own line numbers.

    Byte offsets stay local to the block that produced them -- only `line` and
    `start_line`/`end_line` shift by the block's own start line, matching what
    the extraction records for every other field it does not touch here.
    """
    from .extract import FileFacts

    facts = FileFacts(lang=path_lang, n_lines=text.count("\n") + 1)
    found = False
    for match in _SCRIPT_RE.finditer(text):
        attrs, body = match.group(1), match.group(2)
        script_lang = "typescript" if _SCRIPT_TS_RE.search(attrs) else "javascript"
        offset = text.count("\n", 0, match.start(2))
        block = parse(script_lang, body)
        if block.error:
            continue
        found = True
        for d in block.definitions:
            d.start_line += offset
            d.end_line += offset
        for r in block.references:
            r.line += offset
        for i in block.imports:
            i.line += offset
        facts.definitions.extend(block.definitions)
        facts.references.extend(block.references)
        facts.imports.extend(block.imports)
    if not found:
        facts.reason = "no_symbols"
    return facts
