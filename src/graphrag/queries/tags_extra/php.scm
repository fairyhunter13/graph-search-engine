; The gap: the pinned pack's php/tags.scm captures function_call_expression and
; member_call_expression only. A static call captures nothing, and that is the
; dominant call shape in a Laravel codebase -- User::find, Route::get, DB::table.
(scoped_call_expression name: (name) @name) @reference.call

; The receiver of a static call is a class reference, and it is what a
; constructor-style call must resolve through rather than through the method.
(scoped_call_expression scope: (name) @name) @reference.class
(scoped_call_expression scope: (qualified_name (name) @name)) @reference.class

; new Widget() -- also absent upstream.
(object_creation_expression (name) @name) @reference.class
(object_creation_expression (qualified_name (name) @name)) @reference.class

; A trait and an enum are class-shaped definitions the pack does not capture.
(trait_declaration name: (name) @name) @definition.class
(enum_declaration name: (name) @name) @definition.class

; `use T;` inside a class body composes behaviour, so it is an implementation edge.
(class_declaration
  body: (declaration_list (use_declaration (name) @name))) @reference.implementation
