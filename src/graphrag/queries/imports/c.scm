; #include <stdio.h> -- the angle brackets are part of the node, and they
; are kept: a system header is not a file this repo defines, and the
; brackets are what says so in every answer that prints the module.
(preproc_include path: (system_lib_string) @module)

; #include "local.h"
(preproc_include path: (string_literal (string_content) @module))
