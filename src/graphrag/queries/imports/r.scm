; library(dplyr) and require(ggplot2), where the package is a bare name
((call
   function: (identifier) @_m
   arguments: (arguments (argument value: (identifier) @module)))
 (#any-of? @_m "library" "require" "requireNamespace" "loadNamespace"))

; source("h.R"), where the module is a path this repo may hold
((call
   function: (identifier) @_m
   arguments: (arguments (argument value: (string (string_content) @module))))
 (#any-of? @_m "source" "sys.source"))
