; The pack's cuda/tags.scm captures definitions only. No call, so a caller
; question about CUDA code has never been answerable here. `cpp`'s own
; call pattern is not reused via `QUERY_BASE`: it compiles clean against this
; grammar too, but cuda already captures its own definitions and the two
; concatenated would double every one of them.
(call_expression function: (identifier) @name) @reference.call
