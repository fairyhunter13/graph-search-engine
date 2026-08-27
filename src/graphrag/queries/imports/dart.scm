; import 'p.dart' as p;  and  import 'q.dart' show A, B;
(library_import
  (import_specification (configurable_uri (uri (string_literal) @module))))
(library_import
  (import_specification (configurable_uri (uri (string_literal) @module)) (identifier) @alias))
(library_import
  (import_specification
    (configurable_uri (uri (string_literal) @module))
    (combinator (identifier) @symbol)))

; part 'r.dart'; -- one half of a library, so the scoping needs it
(part_directive (uri (string_literal) @module))
