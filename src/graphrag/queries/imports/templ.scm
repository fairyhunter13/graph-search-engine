; import "fmt" -- templ embeds Go, so the import shape is Go's
(import_spec path: (interpreted_string_literal (interpreted_string_literal_content) @module))
(import_spec
  name: [(package_identifier) (blank_identifier)] @alias
  path: (interpreted_string_literal (interpreted_string_literal_content) @module))
