# graphrag

A code graph search engine on tree-sitter. It answers who calls this, what breaks if I change
this, and what implements this. The semantic sibling is `coderag`, and nothing is imported from it.

## Plan pair

`docs/development-plan.md` and `docs/test-plan.md` are the source of truth for what is built and
what is tested. Read the rows a change touches before starting. Write them back in the same commit.
The `development-plan` and `test-plan` skills own how.

## Routing

`coderag` ranks by meaning, so it finds the code when you have the wrong word for it. `graphrag`
returns an edge, and an edge is in the graph or it is not. Use `coderag` to get the name, then
`graphrag` to get the facts about it. The order never reverses.

Where `graphrag` says a language has no capability for your question, that is an answer. Treat it
as a gap and say so. Never report it as nothing calling the symbol.

## Gate

`.githooks/pre-push` checks the plan pair and the `knowledge/` bundle. Install it with
`git config core.hooksPath .githooks`.
