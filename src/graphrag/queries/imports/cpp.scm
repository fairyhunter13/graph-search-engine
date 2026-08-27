; #include <vector> and #include "local.hpp". The angle brackets stay, as
; in the C query, because a system header is never an in-repo module.
(preproc_include path: (system_lib_string) @module)
(preproc_include path: (string_literal (string_content) @module))

; import std;  -- C++20 modules
(import_declaration name: (module_name (identifier) @module))

; using namespace foo;
(using_declaration (identifier) @module)
