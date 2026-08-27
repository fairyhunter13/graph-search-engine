; import std.stdio;
(import_declaration (imported (module_fqn) @module))

; import std.conv : to;
(import_declaration (imported (module_fqn) @module) (import_bind (identifier) @symbol))
