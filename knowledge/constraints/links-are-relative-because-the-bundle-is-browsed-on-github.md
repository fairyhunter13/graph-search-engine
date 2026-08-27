---
type: Constraint
resource: knowledge/index.md
title: Links here are relative, because the spec and the reference agent disagree
description: "OKF section 6.1 recommends a link that begins with a slash, and the upstream authoring prompt forbids one because it breaks GitHub rendering. Both are right about their own concern, and this bundle lives in a git repo."
tags: [okf, links, github]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T06:15:16Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T09:35:58Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
    digest: sha256:26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101
---

# Two upstream rules, pointing opposite ways

Section 6.1 calls a bundle-relative link the recommended form, because it survives a file
move.[^okf-spec] The reference authoring prompt says the opposite in bold: never start a link with a
slash, because that breaks GitHub rendering.

# This bundle follows the prompt

A bundle in a git repo is read on GitHub, so a link that renders as a 404 is worse than a link that
a file move can break. The reason is written down here because the spec text is what a reader finds
first, and the deviation otherwise reads as a mistake.

`T-40` asserts it: no line in any bundle file carries a link opening at the root.

[^okf-spec]: OKF v0.2 section 6.1, against the reference agent prompt in the same repo.
