; The pack ships no tags.scm for hcl at all. Call only: vanilla Terraform has
; no user-defined functions, only built-in ones (`join`, `lookup`, ...), so
; this capability mostly answers "external" for now. Still a real edge for a
; project-defined provider function once Terraform 1.8+ function blocks land
; in the fleet. Resource, module and variable blocks are references and
; declarations of a different shape and are not attempted here.
(function_call (identifier) @name) @reference.call
