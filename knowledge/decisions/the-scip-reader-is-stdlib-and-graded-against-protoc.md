---
type: Decision
resource: knowledge/decisions/the-scip-reader-is-stdlib-and-graded-against-protoc.md
title: The SCIP reader is a standard-library wire decoder, graded against protoc
description: "SCIP ships no Python binding. Generated code would add a runtime pin that has to move with it, for a tier that is off by default and reads eight messages. The wire format is frozen, so the decoder is the smaller liability."
tags: [scip, protobuf, dependencies, overlay]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T09:15:52Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T09:53:01Z }
sources:
  - id: scip-proto
    resource: https://github.com/sourcegraph/scip/blob/v0.9.0/scip.proto
    digest: sha256:04cb20f2b8be73f6c0376b5b3e84c3ae20ebaff0ad3d23ba2d16f866b395ed7d
  - id: scip-bindings
    resource: https://github.com/sourcegraph/scip/tree/v0.9.0/bindings
---

# What the plan said, and what shipped instead

The plan said to generate `scip_pb2.py` from `scip.proto` with `grpcio-tools` and vendor it. What
shipped is `src/graphrag/scip/wire.py`, 99 lines of protobuf wire decoding on the standard library,
plus `read.py` on top of it.

# Three reasons, and the third is the one that decides it

There is no Python binding for SCIP and none is planned. The repository ships bindings for Go,
Haskell, Java, Kotlin, Rust and TypeScript, and PyPI holds nothing.[^scip-bindings] So either route
starts from the proto.

The plan already required streaming at `Document` granularity, because an index is not held whole.
That means hand-writing the top-level framing walk whatever the reader underneath is. Generated code
would have removed the field parsers and left the walk.

Vendored gencode pins a `protobuf` runtime that has to move with it. That is two pins for a tier
that is off in every project that does not ask for it. The surface actually read is eight messages
and about twenty fields, and the wire format itself is frozen.

# What makes this checkable rather than merely argued

A decoder that agrees with itself proves nothing. `T-102` runs `protoc --decode=scip.Index` over
the same bytes, against the vendored `scip.proto` at tag `v0.9.0`, and compares the counts. The
test skips where `protoc` is absent, because a skip is honest and a pass with one arm missing is
not.

# What would reverse this

A Python binding published by the SCIP project, or a read surface that grows past the eight
messages. Either changes the size of the liability, which is the whole of the argument.

[^scip-proto]: `scip.proto` at tag `v0.9.0`, vendored under `tests/fixtures/scip/`.
[^scip-bindings]: The `bindings/` tree at the same tag, read 2026-08-27.
