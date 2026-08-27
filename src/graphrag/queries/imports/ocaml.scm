; open Core
(open_module module: (module_path) @module)

; module M = Stdlib.List
(module_binding (module_name) @alias body: (module_path) @module)
