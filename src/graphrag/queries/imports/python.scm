; import os
(import_statement name: (dotted_name) @module)

; import os.path as p
(import_statement
  name: (aliased_import
          name: (dotted_name) @module
          alias: (identifier) @alias))

; from a.b import thing
; from . import x        -- relative_import carries the leading dots
(import_from_statement
  module_name: [(dotted_name) (relative_import)] @module
  name: (dotted_name) @symbol)

; from .rel import y as z
(import_from_statement
  module_name: [(dotted_name) (relative_import)] @module
  name: (aliased_import
          name: (dotted_name) @symbol
          alias: (identifier) @alias))
