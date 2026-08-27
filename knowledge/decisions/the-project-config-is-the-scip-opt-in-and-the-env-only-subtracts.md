---
type: Decision
resource: knowledge/decisions/the-project-config-is-the-scip-opt-in-and-the-env-only-subtracts.md
title: The project config is the SCIP opt-in, and the environment switch only subtracts
description: "Two switches that both default off make the first one unreachable. The project asks for the overlay in its own config, and the environment variable exists so an operator can disable the tier on one machine."
tags: [scip, config, overlay]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T09:15:52Z }
---

# The defect this corrects

`SCIP_ENABLED` first read `_env_flag("SCIP_ENABLED", False)`, and `scip.enabled` requires both the
project flag and the environment flag. A project that set `scip: true` in its own `.graphrag.yaml`
therefore got nothing, because the second switch was off and nobody had asked for it to be.

# The rule

The project's `.graphrag.yaml` is the opt-in, and it is the only one. The environment variable
defaults on and can only ever subtract, so an operator disables the tier on one machine without
editing any project. The overlay stays off in every project that does not ask, which is what
"opt-in per project" meant.

# Why the tier is opt-in at all

Every live SCIP indexer needs a resolved build. `scip-python` needs the activated virtualenv,
`scip-typescript` needs `node_modules` on disk, `scip-clang` needs a `compile_commands.json`, and
`scip-java` runs the project's own Gradle or Maven build. Tree-sitter needs none of that. That
asymmetry is the reason SCIP is an overlay and never the floor, and a switch that turned it on
everywhere would make indexing fail in projects that never asked for it.
