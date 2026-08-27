---
type: Decision
resource: src/graphrag/resolve.py
title: Resolution is import-scoped and ranked, and a single edge is never forced
description: "The resolver matches a call site against what the file imports, and emits every survivor with its own confidence."
tags: [resolution, ranking, confidence, tree-sitter]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
sources:
  - id: resolve-module
    resource: src/graphrag/resolve.py
  - id: resolve-test
    resource: tests/test_resolve.py
---

# The choice

A call site names a symbol, and the repo may define that name many times. Two designs were open.
Match the name globally and pick a winner. Or scope the match to what the file imports, score each
survivor, and emit every one of them.

This engine takes the second. Six tiers carry a confidence, from a same-class call at 0.95 down to a
unique global match at 0.30[^resolve-module]. Each surviving candidate becomes its own edge, and the
edge carries the size of the set it came from. A name defined nowhere becomes an external node.

# Why the alternative was rejected

Picking a winner from a global match hides the count. A reader then sees one edge and cannot tell a
fact from a guess. Forcing a name onto an in-repo homonym is worse, because a wrong edge in a graph
answer looks exactly like a right one.

# The measurement this rests on

See [the import-scoping computation](../computations/import-scoping-collapses-the-candidate-set.md)
for the numbers, the pinned corpus and the receipt. It is the attested version of the claim, so this
record cites it rather than repeating its digits.

The test asserts the ratio and a wide band around each arm, never the two
figures[^resolve-test]. A corpus at another tag moves both arms together, and the ratio is what this
design claims.

# The kill criterion that would reverse this

Import scoping stops beating global matching by six times on that corpus. The premise is then gone.
The computation goes blocked with the observed numbers, and this decision is deprecated rather than
relaxed.

A second reversal is open on the other side. If the ranked set collapses to one candidate almost
everywhere, the ranking earns nothing, and the confidence field becomes a cost with no reader.

# What this decision does not cover

The share of call sites the receiver rule refuses. That is a separate fact about syntax, and
[the member-call constraint](../constraints/a-member-call-is-about-43-percent-of-call-sites.md)
holds it.

[^resolve-module]: The tier constants and `_rank` in `src/graphrag/resolve.py`.
[^resolve-test]: `test_import_scoping_collapses_candidates` in `tests/test_resolve.py` asserts bands and a ratio floor.
