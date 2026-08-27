; using System;  -- anchored both ways, so the aliased form is not read here
(using_directive . (identifier) @module .)

; using System.Text;  and  using static System.Math;
(using_directive . (qualified_name) @module)

; using S = System.Text;
(using_directive name: (identifier) @alias (qualified_name) @module)
