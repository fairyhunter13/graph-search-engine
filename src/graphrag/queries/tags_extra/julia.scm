; The pack ships no tags.scm for julia at all. Defs only: a named function's
; own `signature` is grammatically a `call_expression` -- `function baz()` and
; a real call `baz()` are the same node shape, and the base tree-sitter query
; engine has no ancestor-exclusion predicate to tell them apart. nvim-treesitter
; hits the identical wall: github.com/nvim-treesitter/nvim-treesitter/issues/7365.
; A blanket `reference.call` capture would record every function as calling
; itself, which is worse than the absent capability it would replace.
(function_definition
  (signature (call_expression (identifier) @name))) @definition.function
