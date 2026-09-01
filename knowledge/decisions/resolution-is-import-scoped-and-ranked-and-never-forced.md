---
type: Decision
resource: src/graphrag/resolve.py
title: Resolution is import-scoped and ranked, and a single edge is never forced
description: "The resolver matches a call site against what the file imports, and emits every survivor of the best tier with its own confidence."
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
survivor, and emit every survivor of the best tier.

This engine takes the second. Six tiers carry a confidence, from a same-class call at 0.95 down to a
unique global match at 0.30[^resolve-module]. Each surviving candidate becomes its own edge, and the
edge carries the size of the set it came from. A name defined nowhere becomes an external node.

`_rank` keeps the best tier and drops the rest. A candidate reached through an import and a worse
candidate reached only because the repo holds the name are not two answers to rank. Keeping the
second inflates every count, so the emitted set is every survivor of one tier and never a merge of
two.

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

# Where the scoring runs, since 2026-09-01

The tiers, `_rank` and the confidence floor are unchanged, and this decision is unchanged with them.
What moved is where the inputs come from. A same-file and a same-class reference is scored at index
time and stored as an edge. Every reference that leaves its file is scored on read, against rows
rather than a `SymbolTable`. `test_the_two_resolvers_agree_over_this_repo` compares both halves
against the original resolver over this repo's own source, so the ranking is asserted to be the same
ranking and not a second one.

# No surveyed engine ranks, which makes this a contribution and not a debt

The 2026-09-01 survey covered Glean, Kythe, SCIP and each `scip-*` indexer, stack-graphs, CodeQL,
Joern, Sourcegraph, zoekt and ast-grep. Kythe, CodeQL and SCIP push ambiguity to the compiler.
stack-graphs returns every candidate unranked, by stated design. ctags has no resolution model at
all. ast-grep states plainly that it does no cross-file resolution.

So the confidence tiers and `candidate_count` are what this engine has that the field does not. The
second reversal above still stands on its own terms, and it is now the only one open: a ranked set
that collapses to one candidate almost everywhere earns nothing.

# What this decision does not cover

The share of call sites the receiver rule refuses. That is a separate fact about syntax, and
[the member-call constraint](../constraints/a-member-call-is-about-43-percent-of-call-sites.md)
holds it.

[^resolve-module]: The tier constants and `_rank` in `src/graphrag/resolve.py`.
[^resolve-test]: `test_import_scoping_collapses_candidates` in `tests/test_resolve.py` asserts bands and a ratio floor.
