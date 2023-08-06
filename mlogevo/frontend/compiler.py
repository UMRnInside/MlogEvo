from typing import List, Dict, Set, NamedTuple, Any
import os
# for string constants
from ast import literal_eval

from pycparser.c_ast import \
    Compound, Constant, DeclList, Enum, FileAST, \
    FuncDecl, Struct, TypeDecl, Typename, PtrDecl, \
    Typedef, StructRef

from pycparser.c_ast import NodeVisitor
from pycparser import parse_file

from pycparserext_gnuc.ext_c_parser import GnuCParser, \
    FuncDeclExt, Asm

from ..intermediate import Quadruple
from ..intermediate.function import Function, LrValue
from .compilation_error import CompilationError
from .type_util import choose_binaryop_instruction, \
    choose_unaryop_instruction, \
    choose_set_instruction, choose_decl_instruction, \
    extract_attribute, \
    extract_typename, DUMMY_INT_TYPEDECL, \
    CORE_COMPARISONS
from .mlog_object import MlogObjectDefinitionParser, convert_field_name
from .abstract_compiler import AbstractCompiler, FrontendResult


# Stateful AST node visitor & compiler
class Compiler(NodeVisitor, AbstractCompiler):
    def __init__(self):
        self.functions: Dict[str, Function] = {}
        self.current_function: Function = None
        self.globals: Dict[str, LrValue] = {}
        # Temp variables
        self.function_vtmp_count: int = 0
        self.vtmp_count: int = 0
        self.instructions: list = []

        # For builtin items
        self.mlog_object_items: Dict[str, str] = {}
        self.mlog_builtins_items: Dict[str, str] = {}
        self.referred_builtins_items: Set[str] = set()

        self.typedefs = {}
        super().__init__()

    # --- BEGIN INTERNAL UTILITIES ---
    def push(self, instruction) -> None:
        if self.current_function is None:
            self.instructions.append(instruction)
            return
        self.current_function.instructions.append(instruction)

    def peek(self) -> Quadruple:
        if self.current_function is None:
            return self.instructions[-1]
        return self.current_function.instructions[-1]

    # For global variables:
    # it will NOT decorate them
    def decorate_variable(self, variable_name):
        if self.current_function is None:
            return variable_name
        if self.current_function.local_vars.get(variable_name, None) is None:
            # Assume global
            return variable_name
        return F"_{variable_name}@{self.current_function.name}"

    def remove_temp_variable(self, decorated_name):
        if not "__vtmp_" in decorated_name:
            return
        if self.current_function is None:
            self.globals.pop(decorated_name, None)
            return
        first_at = decorated_name.find('@')
        raw_name = decorated_name[1:first_at]
        self.current_function.local_vars.pop(raw_name, None)

    def get_variable(self, var_name, coord) -> LrValue:
        result = None
        if self.current_function is not None:
            result = self.current_function.local_vars.get(var_name, None)
        if result is None:
            result = self.globals.get(var_name, None)
        if result is None:
            # TODO
            raise CompilationError(
                reason=f"Variable {var_name} not found (or referred before declaration)",
                coord = coord
            )
        return result
    # --- END INTERNAL UTILITIES ---
