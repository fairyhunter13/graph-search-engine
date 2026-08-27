; import "./A.sol";
(import_directive source: (string) @module)

; import {B} from "./B.sol";
(import_directive import_name: (identifier) @symbol source: (string) @module)

; import * as C from "./C.sol";
(import_directive alias: (identifier) @alias source: (string) @module)
