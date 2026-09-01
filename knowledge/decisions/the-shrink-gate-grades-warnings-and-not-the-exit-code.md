---
type: Decision
title: The shrink gate grades warnings, because okf check exits 0 on a shrink
description: "Deprecated on 2026-08-29 with the script. `okf check -against HEAD` reports a shrink as a warning and exits 0, so a gate had to grade the printed output. The reasoning still holds, and augment-never-shrink is instruction now."
tags: [okf, gate, provenance, deviation]
status: deprecated
generated: { by: claude/opus-5, at: 2026-08-27T13:07:26Z }
sources:
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

# What the gate did instead, until 2026-08-29

`scripts/check_no_shrink.py` ran the same command and graded its output. A dropped heading and a
lost source were findings. A dropped verification event was a finding only where its actor was gone
from the file as well. The hook built a two-commit repository whose second commit deleted a
heading, and it refused the push where the check accepted that.

The six-rule ruling deleted the script, the hook arm, the CI step and the refusal probe. Six rules
keep a mechanism in this fleet, and augment-never-shrink is not one of them. The rule stays, in the
bundle skill, as instruction.

# What would have to be true to revisit this

`okf check` grows an exit code for a shrink, or `okf verify -stamp` appends an event rather than
moving one. Either one removes the reason for this script.

[^okf]: v0.6.1, the version the gate pins.
