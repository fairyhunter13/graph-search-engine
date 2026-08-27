; require "json"  and  require_relative "helper"
; Ruby imports through a method call, so the predicate is what makes this an
; import query rather than a call query.
((call
   method: (identifier) @_m
   arguments: (argument_list (string (string_content) @module)))
 (#any-of? @_m "require" "require_relative" "load" "autoload"))

; include Comparable  -- a mixin, which is the module a name can come from
((call
   method: (identifier) @_m
   arguments: (argument_list (constant) @module))
 (#any-of? @_m "include" "extend" "prepend"))
