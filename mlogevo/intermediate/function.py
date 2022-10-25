#!/usr/bin/env python3

from dataclasses import dataclass
from pycparser.c_ast import TypeDecl


# function_locals[variable_name] = variable_type (as TypeDecl/PtrDecl/Struct)
# variable_name in function_locals are UNDECORATED
# params: [(parameter_realname_1, typedecl_1), ... ]
@dataclass
class Function:
    name: str
    result_type: TypeDecl
    params: list
    local_vars: dict
    instructions: list

