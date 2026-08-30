---
type: Defect
resource: src/graphrag/discover.py
title: A submodule is invisible to discovery, so initializing one buys no edge
description: "`_git_files` runs `git ls-files --cached --others --exclude-standard`, and `ls-files` lists a gitlink as one entry rather than descending into it. So a materialized submodule contributes nothing to the graph. Measured on a Gen-3 worktree: 9 submodules checked out at their pins, 979 PHP files on disk, and the node count, edge count and `external` share all moved by zero."
tags: [discovery, submodules, php, gen-3, measurement]
status: stable
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
different loss and not a fix. A real fix runs `ls-files` once per submodule and joins the results,
or falls back to the walker inside a submodule. Neither is bought here, because nothing yet needs
it: see below.

# What this settles

The Gen-3 `external` share has exactly one remedy short of a per-language module identity, and this
was it. It does not work today, and making it work is engine work in `discover.py` that must land
**before** any submodule is initialized rather than after.

The disk price is separately unattractive. 71 worktrees declare 1,127 gitlinks over 666 distinct
pins, and the content is already indexed as its own project wherever it is present, so an init
duplicates it. The one worktree grew 82% for nine of twenty.

The pins are also less reachable than a commit-presence test suggests. `ddd-shared`,
`domain-ledger` and `domain-production` are `blob:none` partial clones with a promisor remote: the
commit object is present and its trees are not, so `git cat-file -e <sha>` passes and the checkout
still fails offline. `Shared` failed for exactly that reason, and `Domain/Production` failed at
checkout. Any census that counts a pin by its commit object is an upper bound.

Related: [module identity is Python-shaped](module-identity-is-python-shaped.md).
