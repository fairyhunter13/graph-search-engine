; import 'side-effect' -- the bare source, which every other pattern also carries
(import_statement source: (string (string_fragment) @module))

; import fs from 'fs'
(import_statement
  (import_clause (identifier) @symbol)
  source: (string (string_fragment) @module))

; import {a} from './m'
(import_statement
  (import_clause (named_imports (import_specifier name: (identifier) @symbol)))
  source: (string (string_fragment) @module))

; import {b as c} from './m'
(import_statement
  (import_clause
    (named_imports (import_specifier name: (identifier) @symbol alias: (identifier) @alias)))
  source: (string (string_fragment) @module))

; import * as ns from 'x'
(import_statement
  (import_clause (namespace_import (identifier) @alias))
  source: (string (string_fragment) @module))

; export {k} from './k' -- a re-export is an import for scoping
(export_statement source: (string (string_fragment) @module))

; const q = require('y')
(call_expression
  function: (identifier) @_require
  arguments: (arguments (string (string_fragment) @module))
  (#eq? @_require "require"))
