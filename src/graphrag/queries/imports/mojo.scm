; Mojo spells an import the way Python does, and the grammar is its own.
(import_statement name: (dotted_name) @module)
(import_statement
  name: (aliased_import name: (dotted_name) @module alias: (identifier) @alias))
(import_from_statement
  module_name: [(dotted_name) (relative_import)] @module
  name: (dotted_name) @symbol)
