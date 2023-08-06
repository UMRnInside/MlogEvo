#!/usr/bin/env python3

from dataclasses import dataclass
from typing import NamedTuple, List, Dict
from pycparser.c_ast import TypeDecl
from .ir_quadruple import Quadruple


# function_locals[variable_name] = variable_type (as TypeDecl/PtrDecl/Struct)
# variable_name in function_locals are UNDECORATED
# params: [(parameter_realname_1, typedecl_1), ... ]


class LrValue(NamedTuple):
    vtype: TypeDecl
    # exists LValue and RValue
    name: str
    # "" if in arch==mlog or RValue
    lvalue_address_var: str


@dataclass
class Function:
    name: str
    result_type: TypeDecl
    params: list
    local_vars: Dict[str, LrValue]
    instructions: List[Quadruple]
    attributes: List[str]

