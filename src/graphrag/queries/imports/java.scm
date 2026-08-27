; import java.util.List;  and  import com.x.*;
; A static import spells the member as the last segment, so the module carries
; it. Java has no separate node for the member, and splitting it here would
; guess where the type ends and the method begins.
(import_declaration [(scoped_identifier) (identifier)] @module)
