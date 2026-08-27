; use std::collections::HashMap;  and  use foo;
; The item is the last segment of the path, and Rust has no node that separates
; it from the module. The whole path is the module.
(use_declaration argument: [(identifier) (scoped_identifier)] @module)

; use serde::{Serialize, Deserialize};
(use_declaration
  argument: (scoped_use_list
    path: [(identifier) (scoped_identifier)] @module
    list: (use_list [(identifier) (scoped_identifier)] @symbol)))

; use foo::bar as baz;
(use_declaration
  argument: (use_as_clause
    path: [(identifier) (scoped_identifier)] @module
    alias: (identifier) @alias))

; mod local;  and  extern crate x; -- both name a module this crate holds
(mod_item name: (identifier) @module)
(extern_crate_declaration name: (identifier) @module)
