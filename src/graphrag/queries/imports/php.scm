; use App\Models\User;
; The `.` anchors to the first named child, so the `as P` alias is not read as
; a second module -- both are spelled (name) and only position separates them.
(namespace_use_declaration
  (namespace_use_clause . [(qualified_name) (name)] @module))

; use App\Models\Post as P;
(namespace_use_declaration
  (namespace_use_clause . [(qualified_name) (name)] @module . (name) @alias))

; use App\Traits\{A, B};  -- the group form puts the prefix outside the clause
(namespace_use_declaration
  (namespace_name) @module
  (namespace_use_group
    (namespace_use_clause [(qualified_name) (name)] @symbol)))
