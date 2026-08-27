; import "fmt"
(import_spec path: (interpreted_string_literal (interpreted_string_literal_content) @module))

; import f2 "os"  and  import _ "net/http"
(import_spec
  name: [(package_identifier) (blank_identifier)] @alias
  path: (interpreted_string_literal (interpreted_string_literal_content) @module))
