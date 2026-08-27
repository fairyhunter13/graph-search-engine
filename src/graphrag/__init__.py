"""graphrag: a code graph search engine on tree-sitter.

Flat package by design. `config` imports no sibling, so a cycle is
unresolvable. `scip/` is the only subpackage, because it is optional, isolable
and deletable in one move.
"""

__version__ = "0.1.0"
