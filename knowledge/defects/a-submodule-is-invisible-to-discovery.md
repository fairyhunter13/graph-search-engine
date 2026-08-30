---
type: Defect
resource: src/graphrag/discover.py
title: A submodule is invisible to discovery, so initializing one buys no edge
description: "`_git_files` ran `git ls-files --cached --others --exclude-standard`, and `ls-files` lists a gitlink as one entry rather than descending into it. So a materialized submodule contributed nothing to the graph. Fixed 2026-08-30 by running the command once per gitlink. 2,584 PHP files across 23 worktrees entered the graph, and the resolver then failed to join most of them, which is a second defect this one was hiding."
tags: [discovery, submodules, php, gen-3, measurement]
status: superseded
generated: { by: claude/opus-5, at: 2026-08-30T00:00:00Z }
---

# What was measured

`gen3-app-c/submodule-pin-1.7.6` reports 97.3% of its calls as `external`, the worst share in the
fleet. Its `.gitmodules` declares 20 submodules, and the callee its calls point at,
`Domain/Commitment`, is one of the empty directories. So the callee code was physically absent from
the caller's tree, and the obvious remedy was to put it there.

It was put there. 9 of the 20 were checked out at their exact recorded pins, `Domain/Commitment` at
`29163c191c63` and `Domain/Ledger` at `6e683f4288af` among them. The tree grew from 11 MB to 20 MB
and gained 979 PHP files. Then the project was re-indexed:

| | before | after |
|---|---|---|
| files indexed | 606 | 606 |
| nodes | 3,159 | 3,159 |
| edges | 12,407 | 12,407 |
| CALLS `external` | 9,175 (97.3%) | 9,175 (97.3%) |
| index wall time | 1.0 s | 1.0 s |

Not one number moved.

# Why it happens

`_git_files` prefers `git ls-files` over a directory walk, and the reason in its own docstring is
sound: git already knows what a clone gets and what `.gitignore` drops. But `ls-files` treats a
submodule as a single gitlink entry. It never descends.

Counted on that worktree with the submodules present:

| Invocation | entries | under `Domain/` |
|---|---|---|
| `ls-files --cached --others --exclude-standard` | 714 | 15 |
| `ls-files --cached --recurse-submodules` | 1,754 | 1,056 |

So 1,041 files sat on disk, tracked by their own repository, and discovery listed none of them.

# Why the flag is not the fix

`--recurse-submodules` is refused alongside `--others`:

```
fatal: ls-files --recurse-submodules unsupported mode
```

So adopting it trades every untracked-but-not-ignored file for the submodule content, which is a
different loss and not a fix.

# The fix, 2026-08-30

`_git_files` now runs the same command once per gitlink and joins the results. `_gitlinks` reads
the gitlink paths from `ls-files --stage` rather than from `.gitmodules`, because `.gitmodules`
declares a submodule the tree may never have checked out. An empty submodule directory is skipped.
A depth cap and a visited-realpath set bound the recursion. The paths come back under the outer
root, so `enumerate_files` still derives one relative path and still applies the outer excludes.

Measured over the 23 worktrees that hold a populated submodule:

| | before | after |
|---|---|---|
| PHP files indexed | 5,427 | 8,011 |
| of them inside a gitlink | **0** | **2,584** |

One worktree in detail, `gen3-app-a/submodule-pin_2.1`:

| | before | after |
|---|---|---|
| PHP files | 402 | 530 |
| under `Domain/` | 0 | 128 |
| nodes | 3,136 | 4,583 |
| edges | 13,278 | 16,890 |
| CALLS `external` | 9,614 (94.5%) | 11,363 (93.7%) |

# What the fix uncovered

The `external` share barely moved, and that is the finding. The submodule code is now in the graph
and the resolver does not join it. 2,645 calls name a symbol that is now defined under `Domain/`
and still read `evidence: "external"`. Only 203 resolved.

All 203 have a caller inside `Domain/` too. **Not one edge crosses from the outer project into the
submodule**, which was the whole point of checking it out. The submodule now resolves against
itself, exactly as it already did in its own `domain-*` store. So the cross-boundary edge a reader
wants is still unbought, and no re-index delivers it.

So this defect was hiding a second one. Before the fix, a call into `Domain/` was honestly external:
the callee was absent. After it, the same call is a resolver miss. Read that as a change of cause
and not as a failure of the fix — an unresolvable call became a resolvable one, and
[module identity is Python-shaped](module-identity-is-python-shaped.md) is now the whole of what
stands between it and an edge.

The share of `external` calls whose callee is defined in the same project rose from 11.3% to 30.2%
on that worktree. That is the ceiling any better resolver competes for, and the fix nearly tripled
it.

# What this settles

Discovery is no longer the reason a Gen-3 caller finds no callee. The resolver is. Anyone reading
the Gen-3 `external` share should now go to
[module identity is Python-shaped](module-identity-is-python-shaped.md) first, and never back here.

The disk price stands, and it is the reason not to initialize more submodules than a question
needs. 71 worktrees declare 1,127 gitlinks over 666 distinct pins, and the content is already
indexed as its own project wherever it is present, so an init duplicates it. The one worktree grew
82% for nine of twenty. The fix changes what an already-checked-out submodule buys. It is not a
reason to check one out.

The pins are also less reachable than a commit-presence test suggests. `ddd-shared`,
`domain-ledger` and `domain-production` are `blob:none` partial clones with a promisor remote: the
commit object is present and its trees are not, so `git cat-file -e <sha>` passes and the checkout
still fails offline. `Shared` failed for exactly that reason, and `Domain/Production` failed at
checkout. Any census that counts a pin by its commit object is an upper bound.

Related: [module identity is Python-shaped](module-identity-is-python-shaped.md).
