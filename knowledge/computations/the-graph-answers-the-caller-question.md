---
type: Attested Computation
resource: scripts/two_engine_measure.py
title: The graph answers the caller question, and the retrieval index does not
description: "The measurement that decides whether a second engine earns its process. Over ten caller questions the graph scores F1 1.000, against 0.407 lexical and 0.201 semantic. The class split it once carried is closed."
tags: [routing, measurement, two-engine, attestation]
status: stable
runtime: python
generated: { by: claude/opus-5, at: 2026-08-27T08:30:23Z }
parameters:
  - { name: corpus, type: path, required: true }
executor:
  resource: ../skills/run-two-engine-measure.md
  receipt: [test_node_id, corpus_ref, commit_sha, tree_dirty, outcome, n_questions, f1_graph, f1_lexical, f1_semantic, f1_graph_distinctive, f1_graph_collides]
attester:
  resource: ../attesters/two_engine_receipt.py
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
stale_after: 2027-08-27T00:00:00Z
sources:
  - id: two-engine-run
    resource: scripts/two_engine_measure.py
    last_modified: 2026-08-27T00:00:00Z
  - id: extractor
    resource: src/graphrag/extract.py
---

# The claim

The routing rule says coderag names the symbol and graphrag walks the edges from it. No record
measured that, so the rule was argued and never graded.[^two-engine-run] Ten caller questions over
this repo are scored at file granularity, against a ground truth read by hand. They give the graph
F1 1.000, against 0.441 for lexical retrieval and 0.189 for semantic. So the second engine earns
its process.

# The finding one number hides

Every question carries a class, and the classes agreed only after two fixes. Where a name is called
only through the module that defines it, the graph scores 1.000 on precision and 1.000 on recall.
Where the tree also carries the name as an attribute of something else, precision is 1.000 and
F1 is 1.000.

The first run of this measurement put that second figure at 0.412. The cause was in `extract.py`:
a reference kept the attribute name and discarded the receiver, so `registry.load()` and
`yaml.load()` were one name in the graph. `D-19` captured the receiver.[^extractor] `D-27` then
refused the receiver that is an expression, which is what closed the rest.

# Computation

```yaml
test_node_id: tests/test_two_engine.py::test_the_graph_wins_the_caller_question
corpus_ref: graph-search-engine
```

The corpus is this repo's own tracked tree, `tests/` and `scripts/` included. A caller there is a
caller, and scoping it out prices a correct answer as a false positive.

The test asserts the ordering and the class split, never the digits. A number moves with the corpus,
and the corpus is the repo under work.

The arm figures also move between runs on one commit. Fifteen runs span `d64e8fc`, `396f183`,
`1443efc`, `75bacf7`, `5f3495c`, `4c89a21`, `57de0b0`, `4470719`, `61cbcba`, `58c8a19`, `3ca2c9d`,
`e6f2282`, `7957b6d` and `0f6520c`. They
gave 0.535, 0.510, 0.510, 0.497, 0.497, 0.497, 0.488, 0.454, 0.439, 0.452, 0.407, 0.442, 0.432, 0.441 and 0.466 lexical. They
gave 0.331, 0.316, 0.316, 0.306, 0.306, 0.306, 0.272, 0.294, 0.291, 0.226, 0.201, 0.202, 0.214, 0.189 and 0.176 semantic. The
graph scored 1.000 in every one. The retrieval arms rank by an embedding over a live index, so read them
as the scale of the gap and never as a constant.

The last three agree to three digits, and the fifth ran while the `coderag` daemon was indexing 409
projects. The CLI stopped loading its own model between them, so the arms no longer compete with
the daemon for the card. See `references/the-coderag-cli-holds-its-own-gpu-session.md`.

# What the receipt is for

The ground truth is read by hand, so a score moves when the truth is edited and no engine code
changes. The receipt carries the test node ID and the commit SHA, so a deterministic attester
re-reads both and compares. The class figures are receipt fields for the same reason: a run
reporting one F1 hides the half where the engine loses.

# What the hand truth cost, 2026-08-30

The truth went stale before the engine did. Four real callers were absent from it, and the graph
found all four. The score priced them as false positives, so `T-91` reddened at F1 0.952 while the
engine was right. The census in the module docstring finds them in one command, and it was run for
the failing row only. Run it for every row when a figure moves.

It recurred on 2026-09-01, and from the other direction. The prune work of `D-33` added a
`config.index_path` call in `tests/test_prune.py`; the graph found it, the truth did not list it,
and `distinctive` precision read 0.977 on an otherwise green tree. So a corpus that is the repo
under work moves the truth on every feature, not only on a refactor. The census was re-read for all
ten rows this time, and the four `collides` rows are why it cannot be automated: a regex over
`resolve(`, `load(`, `append(` and `connect(` returns sixty files that call some other symbol of
the same name.

# What would have to be true to revisit this

The graph stops beating both retrieval arms on a caller question. Then the second engine does not
earn its process, and this concept is deprecated rather than relaxed.

Or the receiver is captured and the `collides` class stops losing. Then the split is gone, one
number is honest, and the receipt shrinks with a new concept that names this one.

# What `D-19` did to the second clause, 2026-08-27

Half of it. The `collides` class stopped collapsing, and recall reached 1.000 on both classes. The
split did not close: 0.625 against 1.000 on precision. So the receipt keeps its class fields, and
this concept is amended rather than replaced.

The remaining loss is not a discarded receiver any more. It is a receiver naming a local variable,
which no syntactic rule places, and which this engine now refuses instead of guessing. Closing the
rest needs the type of the receiver, and that is what the SCIP overlay in `D-08` reads.

# What `D-27` closed, 2026-08-27

The other half. `Path(x).resolve()` has a receiver that is an expression, so `extract._member`
returned an empty receiver string. `resolve._receiver_modules` read empty as `decides nothing` and
scored the whole pool, which handed the edge to every homonym in the repo. Twenty false positives
in the `collides` class came from that one shape.

An empty receiver now empties the candidate pool, so the reference leaves the repo as external. The
`collides` class then scored 1.000 on precision, and the split this concept was written around is
closed.

The falsifier above says a closed split shrinks the receipt into a new concept. That is not
followed, and the reason is evidence. The class fields at 1.000 are what shows the split closed,
and a receipt without them cannot show it. So this concept is amended and the fields stay.

# What `D-46` did not move, 2026-09-01

`D-46` moved every cross-file resolution from index time to query time. A caller question no longer
reads a stored edge for a call that leaves its file: it reads the `refs` rows that spell the name,
scores each one against the graph, and keeps the rows whose winning candidate is the target. That is
a different computation reaching the same answer, and this concept is the assertion that it does.

The graph scored F1 1.000 at `61cbcba`, on both classes, with the truth grown to 81 caller entries
by the three new callers `tests/test_resolvedb.py` adds. Nothing here was relaxed to reach it: the
hand truth is what went stale, for the third time in three days. See
[what the hand truth cost](#what-the-hand-truth-cost-2026-08-30): the first run read 0.981 overall
and 0.957 `distinctive` precision, and the three diffs were three real calls in a file this work
wrote. The engine was right and the corpus was behind it.

# What `D-47` did not move, 2026-09-01

`D-47` narrowed the pass to the files the diff names. The graph scored F1 1.000 at `58c8a19`, on
both classes, so a per-file rewrite answers the caller question the way a whole-tree rewrite did.
That is the whole gate on the stage.

The truth grew to 84 entries, and it went stale in two ways this time rather than one.
`tests/test_perfile.py` adds three real calls, which is the pattern of the three runs before it. Two
entries also **moved**: `ledger.append` and `index.index_once` were called from
`src/graphrag/index.py`, and the queue that called them is `src/graphrag/jobs.py` now. A caller that
moves reads as a false positive and a false negative at once, so it costs twice what a new one does.
Both diffs were confirmed against the tree before the corpus was touched.

# What `D-48` did not move, and the first run in five that needed no repair, 2026-09-01

`D-48` made the watcher's paths a hint, so a save hashes the named files and not the tree. The graph
scored F1 1.000 at `3ca2c9d`, on both classes, against the **unchanged** 84-entry truth.

That last clause is the new thing. The four runs before it each found the hand truth stale, and each
repair was a real call the corpus had not listed. This stage added nine test cases and moved none of
them, because the cases it added call the queue and the watcher rather than the symbols the ten
questions ask about. So a stale truth is a property of *which* files a change writes, and not a
property of change itself.

The arms read 0.442 lexical and 0.202 semantic, which is inside the spread the eleven runs before
them describe. Neither arm is a gate. The graph digit is.

# What `D-51` did not move, and the truth grew by one caller, 2026-09-01

`D-51` took the SCIP overlay off the hinted pass. The graph scored F1 1.000 at `e6f2282`, on both
classes.

The first run of this stage did not. It read precision 0.980 on the distinctive class, and the
graph was right again: `tests/test_freshness.py` calls `config.index_path`, and the hand truth
listed no such caller because the file did not exist when the truth was last read. All ten truth
names were censused over the new file before the entry was added. `Path.resolve`, `list.append` and
`sqlite3.connect` also appear there, and each one belongs to a different defining module than its
truth row, so none of the three is an entry. The truth is 85 entries now.

The arms read 0.432 lexical and 0.214 semantic, which is inside the spread the twelve runs before
them describe.

# What `D-40` did not move, and the first run in seven that needed no repair, 2026-09-01

`D-40` gave every language its own module spelling, and on the read side it is the largest change
the resolver has taken: across the fleet, resolved-single `CALLS` edges go 433 to 5,346 and the
external share falls 99.51% to 95.09%. A change that turns four thousand non-edges into edges is
exactly the shape that invents a caller, so this run is the one the concept exists to grade.

The graph scored F1 1.000 at `7957b6d`, on both classes, **on the first run and with no repair to
the hand truth.** Six of the seven runs before it each found a real caller the corpus had not
listed, so a clean first pass is worth stating: the four thousand edges `D-40` adds are Go, PHP and
TypeScript member calls, and this corpus is Python and TypeScript. It confirms the digit rather
than stressing it, and the stress test is the 8,460-file signature diff that rode with the change
instead.

The arms read 0.441 lexical and 0.189 semantic. The semantic arm is the lowest of the fourteen runs
and the lexical arm the highest since `4470719`, which is the spread doing what the section above
says it does and not a finding.

The fifteenth run, at `0f6520c`, holds 1.000 on both classes with no repair to the truth — the second
such run in a row, after six that each needed one. `D-53` adds a column and a reader and touches no
resolution path, so an unmoved graph figure is the reading it should give. Both arms moved again and
in opposite directions, 0.466 lexical and 0.176 semantic, which is the widest spread of the fifteen
in both directions at once and still not a finding.

The sixteenth run, at `0dd0cc4`, holds 1.000 on both classes and needed a repair to get there.
The first pass at `b65db31` read precision 0.962 on the distinctive class, and the graph was right
three times over: `scip/deps.py` calls `config.index_path` and `store.connect`, and
`tests/test_scip_deps.py` calls `index.index_once`. All three files were written by the commit
under test, so the truth was behind by exactly the change being graded. The truth is 88 entries.

That is the seam this concept keeps proving. Stage 6 adds a module that reads the store and a case
that indexes a project, and neither touches a resolution path -- so the only way the digit could
move was through the table, and it did. Two clean runs in a row before this one is not a trend, and
the run that needs a repair is worth as much as the run that does not.

The arms read 0.447 lexical and 0.161 semantic. The semantic arm is the lowest of the sixteen runs,
and the corpus grew by three files between the two readings, which is the spread doing what the
section above says it does.

[^extractor]: `Reference` in `src/graphrag/extract.py` carries `is_member`, the attribute name and, since `D-19`, the receiver.
[^two-engine-run]: Ten caller questions over this repo, 88 ground-truth caller entries, measured 2026-09-01 at commit `0dd0cc4`.
