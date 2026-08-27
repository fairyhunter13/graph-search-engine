; #include <sourcemod> -- the angle brackets are part of the node and stay
(preproc_include path: (system_lib_string) @module)

; #include "local.inc" -- the literal has no content child in this grammar, so
; the quotes come off in the extractor rather than in the pattern.
(preproc_include path: (string_literal) @module)
