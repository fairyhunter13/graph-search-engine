---
type: Decision
resource: src/graphrag/extract.py
title: tree-sitter is declined for chunking and adopted for graphs, because those are two questions
description: "The semantic engine rejected tree-sitter for chunking and dropped a graph tool with it, and that drop stands because this engine asks a different question."
tags: [tree-sitter, scope, two-engine, coderag]
status: stable
generated: { by: claude/opus-5, at: 2026-08-27T10:15:05Z }
verified:
  - { by: process:okf-verify, at: 2026-08-27T11:36:40Z }
sources:
  - id: coderag-chunker
    resource: https://github.com/fairyhunter13/rag-search-engine/blob/main/knowledge/decisions/one-chunker-and-it-is-third-party.md
    digest: sha256:ca22ceea45cc6bcf738dfca2523f60d7b51a7a836266ccc5f9a91c4b82483da6
  - id: coderag-tools
    resource: https://github.com/fairyhunter13/rag-search-engine/blob/main/knowledge/decisions/two-tools-and-the-operator-surface-is-the-cli.md
    digest: sha256:72c3f053a53f429672eb28eb2645218917ead39ba6948fbbe3d9eb4ddf11834b
  - id: extractor
    resource: src/graphrag/extract.py
---

# A reader who finds only the coderag record concludes this work was refused

The semantic sibling carries two records that together read as a ban. One declines tree-sitter for
chunking[^coderag-chunker]. The other drops a `graph` tool and about 4,200 lines of symbol
extraction[^coderag-tools]. It says so in those words, so that nobody proposes the tool again. This
record exists because that pair is the first thing a reader finds. The pair alone gives the wrong
answer.

# The drop is honoured, and it is not overturned

Nothing here re-adds a tool to coderag. Nothing here re-adds symbol extraction to a chunker. The
capability moved out instead. It now has its own engine, its own SQLite store, its own daemon and
its own MCP tools. The line the coderag record drew holds: one engine, one job, and no graph code in
the retrieval path.

# The two questions differ, so the same parser earns a different verdict

Chunking asks where to cut a file so that an embedded window retrieves well. The evidence there
rates the boundary axis lowest. A syntax-aware cut does not beat a sliding window on code. That is a
measured claim about retrieval, and it is not a claim about parsers.

A graph asks a different thing. It asks which byte range is a definition, which byte range is a call
site, and what name each one carries[^extractor]. No sliding window answers that at any size. A
parser is the only thing that answers it, so the decision reverses with the question.

# What this engine takes from the parser, and what it refuses to take

It takes the definition captures, the call captures and the import queries. It refuses the parser as
a text splitter. It also refuses to hand any of this back to the retrieval path. The
[routing rule](../computations/the-graph-answers-the-caller-question.md) is the seam. coderag names
the symbol, and this engine walks the edges from that name.

# What would have to be true to revisit this

The graph stops beating both retrieval arms on a caller question. The measurement that grades that
is the routing computation, and its kill criterion is the kill criterion here. If it fires, the
second engine does not earn its process. The coderag drop then becomes the whole answer again.

[^coderag-chunker]: `one-chunker-and-it-is-third-party.md` in the sibling bundle, which declines the AST chunker on the 864-configuration study.
[^coderag-tools]: `two-tools-and-the-operator-surface-is-the-cli.md` in the sibling bundle, under the heading naming what was dropped.
[^extractor]: `Reference` and the definition walk in `src/graphrag/extract.py`.
