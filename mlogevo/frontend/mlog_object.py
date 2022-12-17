from typing import List, Dict
from pycparser.c_ast import NodeVisitor, \
    PtrDecl, TypeDecl, Decl, Struct

from ..intermediate import Quadruple
from .type_util import extract_typename, extract_attribute


class MlogObjectDefinitionParser(NodeVisitor):
    def __init__(self):
        self.items: Dict[str, str] = {}
        super().__init__()

    def visit_Decl(self, node: Decl):
        if isinstance(node.type, TypeDecl):
            self.items[node.name] = extract_typename(node.type)
        elif isinstance(node.type, PtrDecl):
            # struct MlogObject* controller;
            # _MOBJ controller;
            self.items[node.name] = "struct MlogObject"
        else:
            for child in node:
                self.visit(child)


def convert_field_name(field_name: str):
    field_name = field_name.replace("_", "-")
    return f"@{field_name}"