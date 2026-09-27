; The pack ships no tags.scm for bash at all. Patterns adapted from Aider's
; bash-tags.scm (Apache-2.0), rewritten to this project's `@name` +
; `@definition.*`/`@reference.*` capture convention:
; https://github.com/Aider-AI/aider/blob/main/aider/queries/tree-sitter-language-pack/bash-tags.scm

(function_definition
  name: (word) @name) @definition.function

(command
  name: (command_name (word) @name)) @reference.call
