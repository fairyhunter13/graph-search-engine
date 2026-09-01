---
type: Defect
resource: src/graphrag/scip/ingest.py
title: The overlay believed an artifact older than the file it described
description: "An occurrence is a byte range into the text the indexer read, and this tier writes at confidence 1.0 -- above every ranked candidate it replaces. A file edited after the artifact was written holds different bytes at the same range, so a stale span that still lands on a node is a wrong answer outranking the right one. `ingest` now skips a document whose file is newer than the artifact."
tags: [scip, staleness, edges, confidence]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: ingest
    resource: src/graphrag/scip/ingest.py
  - id: case
    resource: tests/test_scip_ingest.py
---

# What went wrong

`ingest` read the artifact and the file independently and never compared their ages. Everything
downstream is a byte offset: `offsets.Offsets.build` is built from the current text, `_node_at`
matches a node on `(file_id, start_byte, end_byte)`, and `_rewrite_call` replaces the ranked
candidates at a call site byte[^ingest].

If the file changed after the indexer read it, every one of those offsets describes different
bytes. Most of the time that lands on nothing and the document is silently useless. The failure is
the rest of the time: a range that still resolves to a node resolves to the wrong node, and the
edge it writes carries `confidence 1.0` and `evidence 'scip'` -- the tier above `same_class`,
`same_file`, `import` and `package`. A wrong answer that outranks every right one is strictly worse
than the silence this tier promises when it has nothing to say.

The window is not theoretical. The overlay rides the unhinted reconciler rather than a save
(see [the-overlay-ran-on-every-save](the-overlay-ran-on-every-save.md)), and a SCIP indexer over a
large repository runs for minutes. Every file saved during that run is a stale document at ingest.

# What holds it now

`_stale` compares the file's mtime against the artifact's, and a newer file skips the document and
increments `IngestReport.stale`. Skipping leaves the parse's own ranked candidates standing, which
is the weaker answer and the true one -- exactly the promise the tier is built on: SCIP silence is
not the absence of a call.

A file that cannot be stat'd is stale. The alternative -- treating an unreadable file as fresh --
would let the one case with no evidence at all take the highest-confidence path.

# How it is graded

`T-267` runs the same artifact twice over the same store and moves one file's mtime past the
artifact's between the two runs: one call rewritten, then none. Grading the run against itself
rather than against a literal is what makes the second reading mean something.

The predecessor rewrites the call both times. Confirmed by re-running the case against it with the
two `stale` assertions removed, so the failure that was read is behavioural and not the missing
field.

[^ingest]: `src/graphrag/scip/ingest.py`, `_stale`, `_node_at` and `_rewrite_call`.
