---
type: Reference
title: The fleet hook and the nightly sweep are recorded here, not linked
description: "Two decisions rest on mechanisms that live in a private fleet repository. An unauthenticated fetch of that URL reads 404, so every concept citing it stays blocked in the nightly sweep. The facts are written down here instead."
tags: [okf, fleet, freshness, citation]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T13:06:04Z }
---

# What the hook does

`EvaluateVerifiedStamp` refuses any edit that raises the number of `human:` stamps in a concept
under `knowledge/`. The file is `internal/hooks/edit.go` in the `claude-code-workflows` repository.

Its own comment gives the reason. Section 5.3 derives a machine tier from a non-`human:` actor, and
`okf verify` writes one against evidence it just checked. Only a `human:` actor asserts a review
that no agent performed, so only that actor is refused.

# What the nightly sweep does

`okf-verify-nightly.sh` runs `okf verify -run-verifiers` over every bundle on this machine at
04:40. It never passes `-stamp`.

Its own comment gives the design. A timer that writes the stamp it just earned leaves nobody having
decided anything. It catches instead what a stale date cannot catch. An upstream page moved, a
commit was rewritten out of a history, or a path was deleted under a concept that still cites it.

# Why a URL is not the citation

The repository is private, so an unauthenticated fetch reads 404. `okf verify` reports that as
`unreachable` and blocks the concept, every night, forever.

Two decisions here carried that citation and were blocked by it. The sweep is this bundle's
freshness mechanism, so a concept the sweep can never clear turns the mechanism into noise. That is
a contradiction the bundle held against itself, and the resolution is to record the facts where a
reader finds them.

# What would have to be true to revisit this

The repository goes public, or a public mirror carries the two files. The citation then moves back
to a URL, and this record names it.
