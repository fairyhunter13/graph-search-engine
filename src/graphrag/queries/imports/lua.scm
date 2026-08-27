; local m = require("mod")  and  require "other"
((function_call
   name: (identifier) @_m
   arguments: (arguments (string content: (string_content) @module)))
 (#eq? @_m "require"))
