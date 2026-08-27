; Snakemake is Python plus its own directives, and `include:` is an import.
(import_statement name: (dotted_name) @module)
(import_from_statement
  module_name: [(dotted_name) (relative_import)] @module
  name: (dotted_name) @symbol)
(directive arguments: (directive_parameters (string (string_content) @module)))
