"""Extraction throughput, so a regression in query complexity is visible.

Measured 2026-08-27 on CPython `v3.12.7`, 755 files of `Lib` with the test tree
excluded, 12.2 MB, single core, three runs: 117.8, 117.8, 117.9 files per second
and 1.9 MB per second. The method is this test: read every file into memory
first, then time `extract.extract` alone, so disk and decoding do not count.

The floor is 80, which is 32 percent under the measurement. It is a regression
detector and not a target: the margin absorbs a loaded machine, and a change
that costs a third of the throughput is a design change worth seeing.

The plan quoted 334 files per second from an upstream figure that timed a parse
plus a tags query and nothing else. This repo also runs capture normalization,
scope attribution and the import query, so the two numbers measure different
work. The measured one is the one that governs.
"""

from __future__ import annotations

import time

import pytest

from graphrag import config, extract

FLOOR_FILES_PER_S = 80.0
MIN_FILES = 200


def _corpus_texts() -> list[str]:
    root = config.corpus_root() / "Lib"
    texts = []
    for path in sorted(root.rglob("*.py")):
        if "test" in path.parts or "site-packages" in path.parts:
            continue
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return texts


@pytest.mark.corpus
@pytest.mark.slow
def test_extraction_throughput_floor():
    if not (config.corpus_root() / "Lib").is_dir():
        pytest.skip(f"no corpus at {config.corpus_root()}")

    texts = _corpus_texts()
    assert len(texts) >= MIN_FILES, "the corpus is too small to time"

    start = time.perf_counter()
    for text in texts:
        extract.extract("python", text)
    elapsed = time.perf_counter() - start

    rate = len(texts) / elapsed
    assert rate >= FLOOR_FILES_PER_S, (
        f"extraction ran at {rate:.1f} files/s, under the {FLOOR_FILES_PER_S} floor"
    )
