---
type: Constraint
resource: src/graphrag/tools.py
title: mcp 2.0 renames the server class and the tool schema attributes
description: "The 2.0 line renames FastMCP to MCPServer and spells the tool schema attributes in snake_case. A conformance check written against inputSchema raises rather than failing, so it never reports the schema it was written to grade."
tags: [mcp, tools, dependencies, conformance]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T21:30:00Z }
sources:
  - id: pin
    resource: pyproject.toml
  - id: schema-case
    resource: tests/test_tools.py
---

# What changed

`mcp>=1.27` resolves to 2.0.0. The class is `mcp.server.mcpserver.MCPServer`, and the old import
path is gone.[^pin] A `Tool` carries `input_schema` and `output_schema`. The 1.x spelling was
`inputSchema` and `outputSchema`, which matched the wire format rather than the Python one.

# Why the rename bites a conformance test

`T-12` grades the four tool schemas.[^schema-case] Written against `inputSchema` it raises
`AttributeError` at the first tool, which reads as a broken test rather than a broken schema. A
reader then fixes the test and never learns whether the schemas were right.

# What holds it

The pin is `mcp==2.0.*`, not a range, and the in-file comment names the rename. A range moves the
tool decorator and the schema attributes together, under a daemon nothing else guards.

[^pin]: The dependency comment in `pyproject.toml` records the resolution and the reason.
[^schema-case]: `tests/test_tools.py::test_tool_schemas_are_conformant`, which reads both attributes.
