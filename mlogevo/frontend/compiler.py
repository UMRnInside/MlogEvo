from dataclasses import dataclass, field
import sysconfig
import os

from pycparser.c_ast import \
        Compound, Constant, DeclList, Enum, FileAST, \
        FuncDecl, Struct, TypeDecl, Typename, PtrDecl
from pycparser import parse_file

from pycparserext.ext_c_parser import GnuCParser, \
        FuncDeclExt

from ..intermediate import Quadruple
from .parent_node_visitor import ParentNodeVisitor

# function_locals[variable_name] = variable_type (as TypeDecl/PtrDecl/Struct)
# variable_name in function_locals are UNDECORATED
@dataclass
class Function:
    name: str
    params: list
    local_vars: dict

@dataclass
class Loop:
    """start, end: string, label name"""
    start: str
    end: str

# Stateful compiler & ast node visitor
class Compiler(ParentNodeVisitor):
    def __init__(self):
        self.functions = None
        self.current_function = None
        self.globals: dict = None
        self.loops: list = None
        self.loop_end: int = None
        self.special_vars: dict = None
        self.function_locals: dict = None
        self.vtmp_counter: int = None
        self.instructions: list = None
        super().__init__()

    def compile(self, filename: str, use_cpp=True):
        self.functions = {}
        self.current_function = None
        self.globals = {}
        self.vtmp_counter = 0
        self.instructions = []

        ast = parse_file(filename, 
                use_cpp=use_cpp,
                cpp_args=["-I", get_include_path()],
                parser=GnuCParser())
        ast.show()
        self.visit(ast)
        print(self.functions)
        return self.instructions

    def push(self, instruction) -> None:
        self.instructions.append(instruction)

    def decorate_variable(self, variable_name):
        if self.current_function is None:
            return variable_name
        return F"_{variable_name}@{self.current_function.name}"

    # temp variable will be decorated, but this returns a RAW nane
    def create_temp_variable(self, var_type) -> str:
        self.vtmp_counter += 1
        temp_var_name = F"__vtmp_{self.vtmp_counter}"
        self.declare_variable(temp_var_name, var_type)
        return temp_var_name

    def get_variable(self, var_name) -> str:
        result = self.function_locals.get(var_name, None)
        if result is None:
            result = self.globals.get(var_name, None)
        return result

    def declare_variable(self, var_name, var_type):
        if self.current_function is None:
            # is a global variable
            self.globals[var_name] = var_type
        else:
            self.current_function.local_vars[var_name] = var_type

    # Return old or tmp variable name, or its literal
    # require decorated name
    # self.static_cast("3", [int], [int]) -> "3"
    def static_cast(self, src_var, src_typedecl, dst_typedecl) -> str:
        # TODO: PtrDecl
        # TODO: Struct?
        # Assume src_type and dst_type are TypeDecl
        src_typename = extract_typename(src_typedecl)
        dst_typename = extract_typename(dst_typedecl)
        if dst_typename == "int" and src_typename == "double":
            raw_tmp_var = self.create_temp_variable(dst_typedecl)
            tmp_var = self.decorate_variable(raw_tmp_var)
            self.push(Quadruple("ffloor", src_var, "", tmp_var))
            return tmp_var
        return src_var

    # Start visitors
    def visit_FuncDef(self, node):
        func_name = node.decl.name
        # Almost copy-pasted from 
        # https://github.com/SuperStormer/c2logic/blob/master/c2logic/compiler.py
        if func_name in self.functions:
            self.current_function = self.functions[func_name]
        else:
            func_decl = node.decl.type
            if func_decl.args is None or isinstance(func_decl.args.params[0], Typename):
                params = []
            else:
                params = [param_decl.name for param_decl in func_decl.args.params]
            self.current_function = Function(func_name, params, {})

        self.function_locals = self.current_function.local_vars
        self.push(Quadruple("__funcbegin", func_name, ""))
        self.visit(node.body)
        self.push(Quadruple("__funcend", func_name, ""))

        self.functions[func_name] = self.current_function
        self.current_function = None
        self.function_locals = {}

    def visit_Decl(self, node):
        if isinstance(node.type, TypeDecl):
            # decorated_var_name = self.decorate_variable(node.name)
            var_name = node.name
            # Keep TypeDecl, for further Struct/Pointer support
            var_type = node.type
            self.declare_variable(var_name, var_type)
            decorated_name = self.decorate_variable(var_name)
            #print("Decl", var_name, var_type.type)
            if node.init is None:
                return
            rvalue_type, rvalue = self.visit(node.init)
            rvalue_after_cast = self.static_cast(rvalue, rvalue_type, var_type)
            self.push(Quadruple("setl", rvalue_after_cast, "", decorated_name))
            return
        if isinstance(node.type, FuncDecl) or isinstance(node.type, FuncDeclExt):
            func_decl = node.type
            if func_decl.args is None or isinstance(func_decl.args.params[0], Typename):
                params = []
            else:
                params = [param_decl.name for param_decl in func_decl.args.params]
            self.functions[node.name] = Function(node.name, params, {})
            return
        if isinstance(node.type, Struct):
            if node.type.name != "MlogObject":
                raise NotImplementedError(node)
            node.show()
            return
        if isinstance(node.type, PtrDecl):
            #raise NotImplementedError("Pointers are NOT supported in mlog target", node)
            #node.show()
            return
        if isinstance(node.type, Enum):
            raise NotImplementedError(node)
        raise NotImplementedError(node)

    def visit_Assignment(self, node):
        lvalue_decorated = self.decorate_variable(node.lvalue.name)
        lvalue_typedecl = self.get_variable(node.lvalue.name)
        rvalue_typedecl, rvalue = self.visit(node.rvalue)
        rvalue_after_cast = self.static_cast(rvalue, rvalue_typedecl, lvalue_typedecl)
        lvalue_type = extract_typename(lvalue_typedecl)
        print("Assign", node.lvalue, node.op, node.rvalue)
        if node.op == "=":
            if lvalue_type == "int":
                self.push(Quadruple("setl", rvalue_after_cast, "", lvalue_decorated))
            elif lvalue_type == "double":
                self.push(Quadruple("fset", rvalue_after_cast, "", lvalue_decorated))
            return

    # Return (type, value)
    def visit_Constant(self, node):
        return (node.type, node.value)

    def visit_ID(self, node):
        decorated_name = self.decorate_variable(node.name)
        var_typedecl = self.get_variable(node.name)
        return (var_typedecl, decorated_name)


def is_identifier(name) -> bool:
    return len(name) > 0 and ( name[0].isalpha() or name[0] in "_" )

def extract_typename(typedecl) -> str:
    if isinstance(typedecl, str):
        return typedecl
    return typedecl.type.names[0]


def get_include_path():
	if os.name == "posix":
		return sysconfig.get_path("include", "posix_user")
	elif os.name == "nt":
		return sysconfig.get_path("include", "nt")
	else:
		raise ValueError(f"Unknown OS {os.name}")
