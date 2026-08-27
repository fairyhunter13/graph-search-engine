; import Html exposing (div)
(import_clause moduleName: (upper_case_qid) @module)
(import_clause
  moduleName: (upper_case_qid) @module
  exposing: (exposing_list (exposed_value (lower_case_identifier) @symbol)))

; import Json.Decode as D
(import_clause
  moduleName: (upper_case_qid) @module
  asClause: (as_clause name: (upper_case_identifier) @alias))
