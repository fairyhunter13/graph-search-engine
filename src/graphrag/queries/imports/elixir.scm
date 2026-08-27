; import Enum, alias A.B, require Logger, use GenServer.
; Every one is a call, so the predicate is what makes this an import query.
((call target: (identifier) @_m (arguments (alias) @module))
 (#any-of? @_m "import" "alias" "require" "use"))

; alias A.B, as: C
((call
   target: (identifier) @_m
   (arguments (alias) @module (keywords (pair value: (alias) @alias))))
 (#eq? @_m "alias"))
