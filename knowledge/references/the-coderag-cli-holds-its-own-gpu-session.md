---
type: Reference
title: The coderag CLI holds its own GPU session, and the card is shared
description: "The two-engine measurement drives `coderag search` twenty times, and every invocation built its own CUDA session beside the daemon's. The card is 16303 MiB, the daemon holds 7660 MiB and one CLI search added 3114 MiB, so a third consumer exhausted it. `coderag` at `dd0fec0` makes the CLI ask the daemon instead."
tags: [coderag, gpu, measurement, contention]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T23:20:00Z }
---

# Why this is written down here

The facts live in `rag-search-engine`, which this repo never imports and cannot change from here.
They decide how the two-engine measurement fails, so a reader of that measurement needs them.

# What the CLI does

`coderag search` runs the search in the CLI process. `src/coderag/cli.py:63-66` calls
`search.search(...)` directly, and `src/coderag/embed.py:211-224` loads the ONNX session lazily per
process. One semantic search takes about 7 seconds, most of it the load.

Measured on 2026-08-27: the card is 16303 MiB, the `coderag serve` daemon holds 7660 MiB, and one
CLI search adds 3114 MiB.

# What is GPU-only on purpose

`src/coderag/gpu.py:86-95` raises where no GPU provider is available. `gpu.py:112-129` raises
`CPU inference is forbidden` where a session lands on CPU. `gpu.py:98-109` exits the daemon at
start with no GPU. No environment knob selects the device. A CPU fallback would overturn that, so
this repo does not propose one.

# What does not serialize

`src/coderag/embed.py:11` calls `_GPU_INFER_LOCK` the single GPU serializer, and `embed.py:34`
makes it a `threading.RLock`. It holds within one process and not across two, so the daemon and a
CLI invocation each take a full CUDA context with no coordination.

`src/coderag/embed.py:45-51` retries an out-of-memory forward pass at half the batch, matched on
the literal `Failed to allocate memory`. A failure at `cublasCreate` is handle setup rather than a
forward pass, so no smaller batch reaches it and the retry cannot fire. The narrowness is
deliberate and documented there.

# What this cost

A run at `a582e14` exited 1 with `CUBLAS failure 3: the resource allocation failed`. A `coderag`
test suite was driving the daemon at the same time, and the daemon restarted mid-measurement. Three
consumers exhausted the card. The measurement raised rather than scoring the arm zero, which is the
repair `defects/the-unreachable-arm-scored-zero.md` records, and the probe now skips instead.

Nothing had regressed. A run at `1443efc` on a quiet card scores 0.497 lexical and 0.306 semantic
against the graph at 1.000.

# What closed it, 2026-08-28

`coderag` at `dd0fec0` makes the CLI ask the running daemon over MCP rather than search in its own
process. It falls back to a local search only where nothing answers, and there is nothing to share
the card with in that case. The second session this section describes is gone.

Everything above stays written down. The GPU-only rule and the per-process lock did not change, so
a reader of an older receipt still needs them.

Measured after: one semantic search returns in 592 ms rather than about 7 s, and `nvidia-smi`
reports one compute process. A run at `75bacf7` scored 0.497 and 0.306 again, while the daemon was
indexing 409 projects.
