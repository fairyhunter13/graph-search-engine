# Constraint

* [A stale date without an explicit UTC offset reads as fresh
  forever](a-stale-date-needs-an-explicit-utc-offset.md) - OKF section 5 wants an absolute instant.
  An offset-free value parses, passes the standard rule set, and turns freshness checking off with
  no error, so the gate here runs the strict rule set.
* [Links here are relative, because the spec and the reference agent
  disagree](links-are-relative-because-the-bundle-is-browsed-on-github.md) - OKF section 6.1
  recommends a link that begins with a slash, and the upstream authoring prompt forbids one because
  it breaks GitHub rendering. Both are right about their own concern, and this bundle lives in a git
  repo.
* [Extraction runs at about 118 files per second, not
  334](extraction-runs-at-118-files-per-second.md) - The design quoted 334 files per second for a
  parse plus a tags query. This engine also normalizes captures, attributes scope and runs the
  import query, so it measures 117.8 on the same corpus and the floor is set from the measurement.
* [One bad node type disables a whole import query,
  silently](one-bad-node-type-disables-a-whole-query.md) - A tree-sitter query compiles whole or not
  at all, and the extractor returns no matches rather than raising. A single wrong node type makes
  every pattern in the file dead, and the language then reads as one with no import syntax.
* [mcp 2.0 renames the server class and the schema
  attributes](mcp-2-0-renames-the-schema-attributes.md) - The 2.0 line renames FastMCP to MCPServer
  and spells the tool schema attributes in snake_case. A conformance check written against
  inputSchema raises rather than failing, so it never reports the schema it was written to grade.
