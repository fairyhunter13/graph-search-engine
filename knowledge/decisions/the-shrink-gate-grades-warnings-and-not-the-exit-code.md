---
type: Decision
resource: scripts/check_no_shrink.py
title: The shrink gate grades warnings, because okf check exits 0 on a shrink
description: "The plan named `okf check -against HEAD` as a gate. It reports a shrink as a warning and exits 0, and HEAD at push time is the tree it would compare. So the gate runs the same command against the upstream tip and grades what it prints."
tags: [okf, gate, provenance, deviation]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T13:07:26Z }
sources:
  - id: shrink-check
    resource: scripts/check_no_shrink.py
  - id: okf
    resource: https://github.com/fairyhunter13/okf
---

# The command does not fail

`okf check -against <ref>` reads each concept's previous version from git. It reports a dropped
heading and a lost `sources` entry.[^okf] It reports both as warnings, and it exits 0.

A gate that cannot fail is not a gate. So the plan's line, `okf check -against HEAD`, gates
nothing on its own.

# The ref was wrong as well

At push time HEAD is the tree being pushed. Every concept would compare against itself, so the
check would find nothing whatever the push changed. The base is the upstream tip, and a first push
falls back to the parent commit.

# Why `-Werror` is not the fix

`okf verify -stamp` moves the `at` of an existing verification event. The old event then reads as
dropped, and this bundle is stamped on every sweep.

So `-Werror` would block the next push in every repo that stamps, and the rule would be turned off
within a week. That is the honest reason this deviates.

# What the gate does instead

`scripts/check_no_shrink.py` runs the same command and grades its output.[^shrink-check] A dropped
heading and a lost source are findings. A dropped verification event is a finding only where its
actor is gone from the file as well.

The hook proves the check refuses before it trusts it. It builds a two-commit repository whose
second commit deletes a heading, and it fails the push where the check accepts that.

# What would have to be true to revisit this

`okf check` grows an exit code for a shrink, or `okf verify -stamp` appends an event rather than
moving one. Either one removes the reason for this script.

[^okf]: v0.6.0, the version the gate pins.
[^shrink-check]: The script's own docstring carries this reason, and no concept did until now.
