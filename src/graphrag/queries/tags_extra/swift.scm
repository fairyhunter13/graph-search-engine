; The pack's swift/tags.scm captures definitions and protocol conformance
; only. A free-function call site -- `baz()` -- carries no capture upstream.
; A member call (`a.b()`) is a `navigation_expression` and stays uncaptured:
; it names a receiver this project cannot yet resolve through.
(call_expression (simple_identifier) @name) @reference.call
