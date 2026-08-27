# Constraint

* [18 of the 68 tagged grammars emit no call capture, so capability is per
  capture](eighteen-of-the-sixty-eight-emit-no-call-capture.md) - 50 of the 68 tagged grammars
  capture a call and 18 do not, so a tags file and a caller answer are different questions.
* [68 of 371 grammars ship a tags file, so any language means parsing and not
  symbols](sixty-eight-of-371-grammars-ship-a-tags-file.md) - The pack parses 371 languages and only
  68 carry a tags query, so a grammar with no tags file yields a tree and no symbol.
* [A member call is about 43% of call sites, and a syntactic rule cannot reach
  it](a-member-call-is-about-43-percent-of-call-sites.md) - About 43% of call sites are member
  calls, and no syntactic rule places the receiver, so the engine refuses those sites rather than
  guessing.
* [A pass reparses the tree, because resolution is global](a-pass-reparses-the-tree-because-resolution-is-global.md) - Every reference is
  scored against the whole symbol table. A pass that reparsed only the edited file would price
  every other file as a repo that does not define the name. Per-file facts are not persisted, so
  there is nothing to reuse.
* [A stale date without an explicit UTC offset reads as fresh
  forever](a-stale-date-needs-an-explicit-utc-offset.md) - OKF section 5 wants an absolute instant.
  An offset-free value parses, passes the standard rule set, and turns freshness checking off with
  no error, so the gate here runs the strict rule set.
* [An occurrence range comes in three shapes, and scip-java emits only the
  newest](an-occurrence-range-comes-in-three-shapes.md) - SCIP v0.8.0 deprecated the flat integer
  range for a typed one, and scip-java emits only the typed form, so a one-shape reader gets
  nothing.
* [An unreachable daemon and an absent edge look identical, and mean opposite
  things](an-unreachable-daemon-is-not-an-absent-edge.md) - A session that reads a missing
  structural answer as nothing calling the symbol produces a confidently wrong result. The notice
  and the tools each say which of the two happened.
* [An unset position_encoding does not mean one
  thing](an-unset-position-encoding-does-not-mean-one-thing.md) - Most indexers leave the field at
  0, and 0 means UTF-8 on scip-go and UTF-16 on scip-python. So the fallback is keyed on the tool
  name, and an unknown name is an error rather than a guess.
* [Every SCIP indexer needs a resolved build and tree-sitter needs
  none](every-scip-indexer-needs-a-resolved-build.md) - A SCIP index needs the project's
  dependencies resolved and its build working, and a tree-sitter parse needs only the bytes of one
  file.
* [Extraction runs at about 118 files per second, not
  334](extraction-runs-at-118-files-per-second.md) - The design quoted 334 files per second for a
  parse plus a tags query. This engine also normalizes captures, attributes scope and runs the
  import query, so it measures 117.8 on the same corpus and the floor is set from the measurement.
* [Links here are relative, because the spec and the reference agent
  disagree](links-are-relative-because-the-bundle-is-browsed-on-github.md) - OKF section 6.1
  recommends a link that begins with a slash, and the upstream authoring prompt forbids one because
  it breaks GitHub rendering. Both are right about their own concern, and this bundle lives in a git
  repo.
* [mcp 2.0 renames the server class and the schema
  attributes](mcp-2-0-renames-the-schema-attributes.md) - The 2.0 line renames FastMCP to MCPServer
  and spells the tool schema attributes in snake_case. A conformance check written against
  inputSchema raises rather than failing, so it never reports the schema it was written to grade.
* [One bad node type disables a whole import query,
  silently](one-bad-node-type-disables-a-whole-query.md) - A tree-sitter query compiles whole or not
  at all, and the extractor returns no matches rather than raising. A single wrong node type makes
  every pattern in the file dead, and the language then reads as one with no import syntax.
* [SymbolInformation.kind is a per-indexer capability, and 0 does not mean
  unspecified](symbol-information-kind-is-a-per-indexer-capability.md) - Five of the ten live SCIP
  indexers leave the kind field at 0, so 0 means the tool declined to answer.
* [The pack ships its queries in the wheel and downloads a parser on first
  use](the-pack-ships-queries-and-downloads-parsers-on-first-use.md) - Query text arrives with the
  install, and a parser arrives over the network on first use, so an air-gapped install needs a
  seeded cache.
