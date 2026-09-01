---
type: Defect
resource: knowledge/computations/the-graph-answers-the-caller-question.md
title: A tally written in prose had no gate
description: "Three audits in one day each corrected wrong figures in the same records, and each round wrote a new wrong one while fixing the last. Nine false claims in total. Every gate this repo runs — the suite, ruff, okfrules and the plan-pair test — passes a sentence that counts wrong, because none of them reads a number written in prose. T-337 now grades the one tally that drifted three times; the rest of the class is held by nothing but a reader who recounts."
tags: [knowledge-bundle, drift, gate, measurement]
status: stable
generated: { by: claude/opus-5, at: 2026-09-01T00:00:00Z }
sources:
  - id: gate
    resource: tests/test_bundle.py
  - id: concept
    resource: knowledge/computations/the-graph-answers-the-caller-question.md
  - id: log
    resource: knowledge/log.md
---

# What happened

`the-graph-answers-the-caller-question.md` records one measurement per run and has been re-measured
seventeen times. Each run appends a sha, two arm figures and a paragraph. Sentences elsewhere in the
file count those runs, rank those figures and name populations of them.

Three audits on 2026-09-01 found nine false claims across the bundle and the plan pair. Three of
them were written by the round that was fixing the previous three.

# The two shapes

**A claim anchored to the end of a list that is appended to.** *The last three agree to three
digits* was true at `9f405c3`, when the file listed six runs and the last three each read 0.497
lexical. Eleven runs landed after it and the sentence never moved. Its own predecessor, *the last
two agree*, had already rotted once and been patched forward instead of re-anchored. The fix is an
ordinal counted from the start — the fourth, fifth and sixth — which no append moves.

**A count over a population the sentence never states.** *Three runs since this concept was written
have needed no repair* is false because the first six runs needed none either: the hand truth sat
flat at 70 entries across all of them, and all seventeen runs postdate the concept. The boundary
that makes the count mean anything is the seventh run, where the truth first went stale. Three
headings in the file counted clean runs from three different boundaries, which is how the number
drifted three times without any of them contradicting each other on the page.

A third claim, *the lexical arm the highest since `4470719`*, was false the day `1dd0fe9` wrote it:
`61cbcba` read 0.452 and `3ca2c9d` 0.442 against the 0.441 it calls highest, and the figure list at
that commit was identical to today's. It was never true, and it survived three audits.

# Why no gate saw it

The suite grades behaviour, `ruff` grades syntax, `okfrules` grades bundle structure, and
`tests/test_plan_pair.py` grades the plan tables. A sentence that counts wrong is well-formed to
every one of them. The receipt attester is the closest thing here to a numeric gate, and it compares
a receipt against a claim block — not a claim against the prose around it.

# What holds it now

`T-337` reads the arm paragraph and asserts the spelled run count equals the number of lexical
figures and the number of semantic figures. Run against `40690e6` it fails 11 against 10: that
commit shipped *Ten runs* over eleven figures in each arm, and every gate passed it.

The sha list is deliberately not counted. One early run's hex is lost to a history rewrite, and the
paragraph names other commits inside the same span.

# What it does not hold, stated so the next audit need not re-derive it

`T-337` grades one paragraph of one file, and only the countable half of the class. It cannot see a
superlative, a population left unstated, or a stale `file.py:NN` citation — the shapes behind six of
the nine findings. Those are held by nothing.

Writing them out of the bundle is cheaper than grading them, so the rule is: anchor an ordinal from
the start of a list and never from its end, state the population a count runs over, and prefer a
named guard to a line number when citing code.
