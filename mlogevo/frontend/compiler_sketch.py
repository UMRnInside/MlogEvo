from dataclasses import dataclass, field
from typing import List, Dict, Set
import sysconfig
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
from ..intermediate.function import Function
from .compilation_error import CompilationError
from .type_util import choose_binaryop_instruction, \
    choose_unaryop_instruction, \
    choose_set_instruction, choose_decl_instruction, \
    extract_attribute, \
    extract_typename, DUMMY_INT_TYPEDECL, \
    CORE_COMPARISONS
from .mlog_object import MlogObjectDefinitionParser, convert_field_name
from .parent_node_visitor import ParentNodeVisitor
from .abstract_compiler import AbstractCompiler, FrontendResult


# Stateful compiler & ast node visitor
# TODO: this stateful compiler is a mess, consider breaking it into several components
class CompilerSketch(ParentNodeVisitor, AbstractCompiler):
    def __init__(self):
        self.functions = {}
        self.current_function = None
        self.globals: dict = {}
        self.loops: list = []
        self.loop_end: int = 0
        self.vtmp_count: int = 0
        self.function_vtmp_count: int = 0
        self.instructions: list = []
        self.mlog_object_items: Dict[str, str] = {}
        self.mlog_builtins_items: Dict[str, str] = {}
        self.referred_builtins_items: Set[str] = set()

        self.typedefs = {}

        super().__init__()

    def compile(self, filename: str, use_cpp=True, cpp_args=None) -> FrontendResult:
        if cpp_args is None:
            cpp_args = []
        include_path = get_include_path()
        if len(include_path) > 0:
            cpp_args = cpp_args + ["-I", include_path]
        ast = parse_file(filename,
                         use_cpp=use_cpp,
                         cpp_args=cpp_args,
                         parser=GnuCParser())
        self.visit(ast)
        referred_builtins = []
        for field in self.referred_builtins_items:
            referred_builtins.append(
                Quadruple(
                    instruction=choose_decl_instruction(self.mlog_builtins_items[field]),
                    dest=convert_field_name(field)
                )
            )
        return FrontendResult({}, referred_builtins+self.instructions, self.functions)

    def push(self, instruction) -> None:
        if self.current_function is None:
            self.instructions.append(instruction)
            return
        self.current_function.instructions.append(instruction)

    def peek(self):
        if self.current_function is None:
            return self.instructions[-1]
        return self.current_function.instructions[-1]

    def heuristic_assign(self, src_var, dest_var, dest_typedecl):
        """ Peek last instruction that generates temp variable.
        Redirect last instruction to dest_var if feasible.
        Require decorated variable name. """
        copy_inst = choose_set_instruction(dest_typedecl)
        if is_mlogev_temp_var(src_var):
            if self.peek().dest == src_var:
                self.peek().dest = dest_var
                self.remove_temp_variable(src_var)
                return
            output_vars_ref = self.peek().output_vars
            if len(output_vars_ref) == 1 and output_vars_ref[0] == src_var:
                output_vars_ref[0] = dest_var
                self.remove_temp_variable(src_var)
                return
        self.push(Quadruple(copy_inst, src_var, "", dest_var))

    # For global variables:
    # it will NOT decorate them
    def decorate_variable(self, variable_name):
        if self.current_function is None:
            return variable_name
        if self.current_function.local_vars.get(variable_name, None) is None:
            # Assume global
            return variable_name
        return F"_{variable_name}@{self.current_function.name}"

    # temp variable should be decorated
    def create_temp_variable(self, var_type, autodecorate=True) -> str:
        temp_var_name: str
        if self.current_function is None:
            self.vtmp_count += 1
            temp_var_name = F"__vtmp_{self.vtmp_count}"
        else:
            self.function_vtmp_count += 1
            temp_var_name = F"__vtmp_{self.function_vtmp_count}"
        self.declare_variable(temp_var_name, var_type)
        if autodecorate:
            temp_var_name = self.decorate_variable(temp_var_name)
        decl_inst = choose_decl_instruction(var_type)
        if len(decl_inst) > 0:
            self.push(Quadruple(decl_inst, dest=temp_var_name))
        return temp_var_name

    def remove_temp_variable(self, decorated_name):
        if not "__vtmp_" in decorated_name:
            return
        if self.current_function is None:
            self.globals.pop(decorated_name, None)
            return
        first_at = decorated_name.find('@')
        raw_name = decorated_name[1:first_at]
        self.current_function.local_vars.pop(raw_name, None)

    def get_variable(self, var_name, coord) -> tuple:
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
        return result, self.decorate_variable(var_name)

    def declare_variable(self, var_name, var_type):
        if self.current_function is None:
            # is a global variable
            self.globals[var_name] = var_type
        else:
            self.current_function.local_vars[var_name] = var_type

    def extract_actual_typename(self, target) -> str:
        name = extract_typename(target)
        return extract_typename(self.typedefs.get(name, target))

    # Return old or tmp variable name, or its literal
    # require decorated name
    # self.static_cast("3", [int], [int]) -> "3"
    def static_cast(self, src_var, src_typedecl, dst_typedecl) -> str:
        # TODO: PtrDecl
        # TODO: Struct?
        # Assume src_type and dst_type are TypeDecl
        src_typename = self.extract_actual_typename(src_typedecl)
        dst_typename = self.extract_actual_typename(dst_typedecl)
        if dst_typename == "int" and src_typename == "double":
            tmp_var = self.create_temp_variable(dst_typedecl, True)
            self.push(Quadruple("cvtf64_i32", src_var, "", tmp_var))
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
                params = [(param_decl.name, param_decl.type)
                          for param_decl in func_decl.args.params]
            specs = [extract_attribute(attr) for attr in node.decl.funcspec] or ["default", ]
            self.current_function = Function(func_name, func_decl.type, params, dict(params), [], specs)

        self.function_vtmp_count = 0
        # self.function_locals = self.current_function.local_vars
        self.functions[func_name] = self.current_function

        ir_attributes = ",".join(self.current_function.attributes)
        self.push(Quadruple("__funcbegin", func_name, "", ir_attributes))
        decl_inst = choose_decl_instruction(self.current_function.result_type)
        if len(decl_inst) > 0:
            self.push(Quadruple(decl_inst, dest=f"result@{func_name}"))
        self.visit(node.body)
        self.push(Quadruple("__funcend", func_name, ""))

        self.current_function = None
        # self.function_locals = {}

    def visit_Decl(self, node):
        if isinstance(node.type, TypeDecl):
            var_name = node.name
            # Keep TypeDecl, for further Struct/Pointer support
            # var_type = node.type
            var_type = self.typedefs.get(extract_typename(node.type), node.type)
            
            self.declare_variable(var_name, var_type)
            decorated_name = self.decorate_variable(var_name)
            decl_inst = choose_decl_instruction(var_type)
            if decl_inst:
                self.push(Quadruple(decl_inst, dest=decorated_name))
            # print("Decl", var_name, var_type.type)
            if node.init is None:
                return
            rvalue_type, rvalue = self.visit(node.init)
            rvalue_after_cast = self.static_cast(rvalue, rvalue_type, var_type)
            self.heuristic_assign(rvalue_after_cast, decorated_name, var_type)
            return
        if isinstance(node.type, FuncDecl) or isinstance(node.type, FuncDeclExt):
            func_decl = node.type
            if func_decl.args is None or isinstance(func_decl.args.params[0], Typename):
                params = []
            else:
                params = [(param_decl.name, param_decl.type)
                          for param_decl in func_decl.args.params]
            specs = [extract_attribute(attr) for attr in node.decl.funcspec] or ["default", ]
            self.functions[node.name] = Function(node.name, func_decl.type, params, dict(params), [], specs)
            return
        if isinstance(node.type, Struct):
            if node.type.name == "MlogObject":
                struct_parser = MlogObjectDefinitionParser()
                struct_parser.visit(node.type)
                self.mlog_object_items = struct_parser.items
                return
            if node.type.name == "MLOG_BUILTINS":
                struct_parser = MlogObjectDefinitionParser()
                struct_parser.visit(node.type)
                self.mlog_builtins_items = struct_parser.items
                return
            raise CompilationError(
                reason=f"struct support is not implemented yet",
                coord=node.coord
            )
        if isinstance(node.type, PtrDecl):
            # raise NotImplementedError("Pointers are NOT supported in mlog target", node)
            # node.show()
            return
        if isinstance(node.type, Enum):
            raise NotImplementedError(node)
        raise NotImplementedError(node)

    def visit_Assignment(self, node):
        # lvalue_decorated = self.decorate_variable(node.lvalue.name)
        lvalue_typedecl, lvalue_decorated = self.get_variable(node.lvalue.name, node.coord)
        rvalue_typedecl, rvalue = self.visit(node.rvalue)
        # print("Assign", node.lvalue, node.op, node.rvalue)
        if node.op == "=":
            rvalue_after_cast = self.static_cast(rvalue, rvalue_typedecl, lvalue_typedecl)
            self.heuristic_assign(rvalue_after_cast, lvalue_decorated, lvalue_typedecl)
            return lvalue_typedecl, lvalue_decorated

        binary_op = node.op[:-1]
        result_typedecl, inst = choose_binaryop_instruction(
            binary_op, lvalue_typedecl, rvalue_typedecl
        )
        if self.extract_actual_typename(result_typedecl) == self.extract_actual_typename(lvalue_typedecl):
            self.push(Quadruple(inst, lvalue_decorated, rvalue, lvalue_decorated))
            return lvalue_typedecl, lvalue_decorated

        temp_var = self.create_temp_variable(result_typedecl, True)
        self.push(Quadruple(inst, lvalue_decorated, rvalue, temp_var))
        temp_after_cast = self.static_cast(temp_var, result_typedecl, lvalue_typedecl)
        self.heuristic_assign(temp_after_cast, lvalue_decorated, lvalue_typedecl)
        return lvalue_typedecl, lvalue_decorated

    # Return (type, value)
    def visit_Constant(self, node):
        typename = self.extract_actual_typename(node.type)
        if typename in ("double", "float"):
            value = str(float(node.value))
            return node.type, value
        if typename == "string":
            # Treat string as a MlogObject
            return "struct MlogObject", node.value
            pass
        return node.type, node.value

    def visit_ID(self, node):
        # Reserved for Extended Asm in functions
        if self.current_function is not None \
                and node.name == "__mlogev_function_return_value__":
            return self.current_function.result_type, f"result@{self.current_function.name}"
        # decorated_name = self.decorate_variable(node.name)
        var_typedecl, decorated_name = self.get_variable(node.name, node.coord)
        return var_typedecl, decorated_name

    def visit_Cast(self, node):
        src_typedecl, src_var = self.visit(node.expr)
        src_typename = self.extract_actual_typename(src_typedecl)
        dst_typename = self.extract_actual_typename(node.to_type.type)
        # Mlog Object can contain int or double
        if src_typename == dst_typename or dst_typename == "struct MlogObject":
            return src_typedecl, src_var

        result_var = self.static_cast(src_var, src_typedecl, node.to_type.type)
        return node.to_type.type, result_var

    def visit_Typedef(self, node: Typedef):
        typedecl = node.type
        while extract_typename(typedecl) in self.typedefs.keys():
            name = extract_typename(typedecl)
            if name == self.typedefs[name]:
                break
            typedecl = self.typedefs[name]
        self.typedefs[node.name] = typedecl
        pass

    # May be generated by comma operators
    def visit_ExprList(self, node):
        var_typedecl = None
        name_or_value = None
        for child in node:
            var_typedecl, name_or_value = self.visit(child)
        return var_typedecl, name_or_value

    def visit_UnaryOp(self, node):
        var_typedecl, var_realname = self.visit(node.expr)
        # print("UnaryOp", node)
        if node.op in ("-", "~"):
            result_var = self.create_temp_variable(var_typedecl, True)
            result_typedecl, unary_inst = choose_unaryop_instruction(
                node.op, var_typedecl
            )
            self.push(Quadruple(unary_inst, var_realname, "", result_var))
            return result_typedecl, result_var
        if node.op in ("p++", "p--", "++", "--"):
            # var_realname = self.decorate_variable(node.expr.name)
            # var_typedecl = self.get_variable(node.expr.name)

            result_var = var_realname
            if node.op in ("p++", "p--"):
                copy_inst = choose_set_instruction(var_typedecl)
                # Postincrement: copy value
                result_var = self.create_temp_variable(var_typedecl, True)
                self.push(Quadruple(copy_inst, var_realname, "", result_var))
            # Avoid hardcoded IR
            # result TypeDecl is always var_typedecl
            _, binary_inst = choose_binaryop_instruction(
                node.op[1], var_typedecl, var_typedecl
            )
            self.push(Quadruple(binary_inst, var_realname, "1", var_realname))
            return var_typedecl, result_var
        if node.op == "!":
            result_var = self.create_temp_variable(var_typedecl, True)
            inst, result_typedecl = choose_binaryop_instruction(
                "==", var_typedecl, var_typedecl
            )
            self.push(Quadruple(inst, var_realname, "0", result_var))
            return result_typedecl, result_var

        # TODO: & (address), * (dereference) in mlogmem arch?
        return var_typedecl, var_realname

    def visit_Label(self, node):
        self.push(Quadruple("label", node.name))
        self.visit(node.stmt)

    def visit_Goto(self, node):
        self.push(Quadruple("goto", node.name))

    def visit_Return(self, node):
        function_name = self.current_function.name
        if node.expr is not None:
            r_typedecl, r_varname = self.visit(node.expr)
            result_typedecl = self.current_function.result_type
            result = r_varname
            if self.extract_actual_typename(r_typedecl) \
                    != self.extract_actual_typename(result_typedecl):
                result = self.static_cast(r_varname, r_typedecl, result_typedecl)

            dest = f"result@{function_name}"
            self.heuristic_assign(result, dest, result_typedecl)
        self.push(Quadruple("__return", function_name))

    def visit_FuncCall(self, node):
        function_name = node.name.name
        args = node.args or []
        # NOTE: this is the first builtin function in MlogEvo
        # The print() w/o va_arg
        if function_name == "print":
            asm_lines = []
            input_vars = []
            for arg in args:
                # arg_varname could be a string though
                arg_typedecl, arg_varname = self.visit(arg)
                asm_lines.append(f"print {arg_varname}")
                input_vars.append(arg_varname)
            asm_ir = Quadruple("asm_volatile")
            asm_ir.input_vars = input_vars
            asm_ir.raw_instructions = asm_lines
            self.push(asm_ir)
            return None, ""

        func = self.functions.get(function_name, None)
        if func is None:
            raise ValueError(f"{function_name} is not a function (or not declared)")
        # if len(func.params) != len(args):
        #    raise ValueError(f"{function_name} expect {len(func.params)} params, got {len(args)}")
        for param_decl, arg in zip(func.params, args):
            param_realname = f"_{param_decl[0]}@{function_name}"
            arg_typedecl, arg_varname = self.visit(arg)
            real_argument = arg_varname
            param_type = self.extract_actual_typename(param_decl[1])
            if self.extract_actual_typename(arg_typedecl) != param_type:
                real_argument = self.static_cast(arg_varname, arg_typedecl, param_decl[1])
            self.heuristic_assign(real_argument, param_realname, param_decl[1])
        self.push(Quadruple("__call", function_name))
        decl_inst = choose_decl_instruction(func.result_type)
        if decl_inst != "":
            self.push(Quadruple(decl_inst, dest=f"result@{function_name}"))
        # Assume a function returns something
        return func.result_type, f"result@{function_name}"

    def visit_Asm(self, node: Asm):
        result_ir = Quadruple("asm")
        if "volatile" in node.asm_keyword:
            result_ir = Quadruple("asm_volatile")
        # node(Asm) -> template(ExprList)
        for constant in node.template:
            result_ir.raw_instructions.extend(literal_eval(constant.value).splitlines())

        # TODO: assume expr is ID, constraints is discarded
        for operand in (node.input_operands or []):
            constraints, expr = extract_asm_operand(operand)
            typedecl, var_name = self.visit(expr)
            result_ir.input_vars.append(var_name)

        for operand in (node.output_operands or []):
            constraints, expr = extract_asm_operand(operand)
            # NOTE: __mlogev_function_return_value__ handled in visit_ID()
            typedecl, var_name = self.visit(expr)
            result_ir.output_vars.append(var_name)
            # https://gcc.gnu.org/onlinedocs/gcc/Modifiers.html
            if constraints[0] == '+':
                result_ir.input_vars.append(var_name)
        self.push(result_ir)

    def visit_StructRef(self, node: StructRef):
        # NOTE: this ignores node.type ( . or -> )
        base_typedecl, base_var = self.visit(node.name)
        base_type = self.extract_actual_typename(base_typedecl)
        if not base_type.startswith("struct "):
            raise CompilationError(
                reason=f"Attempted to use StructRef on non-struct item",
                coord=node.coord
            )
        field_name = node.field.name
        result_type = None
        result_var = None
        try:
            if base_type == "struct MlogObject":
                result_type = self.mlog_object_items[field_name]
                result_var = self.create_temp_variable(result_type)
                asm_ir = Quadruple("asm")
                asm_ir.raw_instructions.append(f"sensor %0 %1 {convert_field_name(field_name)}")
                asm_ir.input_vars.append(base_var)
                asm_ir.output_vars.append(result_var)
                self.push(asm_ir)
            elif base_type == "struct MLOG_BUILTINS":
                result_type = self.mlog_builtins_items[field_name]
                result_var = convert_field_name(field_name)
                self.referred_builtins_items.add(field_name)
        except KeyError as e:
            raise CompilationError(
                reason=f"`{base_type}` does not have field `{e.args[0]}`",
                coord=node.coord
            )
        return result_type, result_var



def extract_asm_operand(operand):
    # FuncCall -> name(Constant)
    constraints = operand.name.value
    # FuncCall -> args(ExprList) -> exprs[0]
    expr = operand.args.exprs[0]
    return constraints, expr


def is_mlogev_temp_var(varname):
    return varname.startswith("__vtmp_") or varname.startswith("___vtmp_")


def get_include_path() -> str:
    if os.name == "posix":
        return sysconfig.get_path("include", "posix_user")
    elif os.name == "nt":
        return sysconfig.get_path("include", "nt")
    return ""
