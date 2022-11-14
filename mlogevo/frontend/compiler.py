from dataclasses import dataclass, field
import sysconfig
import os
# for string constants
from ast import literal_eval

from pycparser.c_ast import \
    Compound, Constant, DeclList, Enum, FileAST, \
    FuncDecl, Struct, TypeDecl, Typename, PtrDecl

from pycparser.c_ast import NodeVisitor
from pycparser import parse_file

from pycparserext_gnuc.ext_c_parser import GnuCParser, \
    FuncDeclExt

from ..intermediate import Quadruple
from ..intermediate.function import Function
from .type_util import choose_binaryop_instruction, \
    choose_unaryop_instruction, \
    choose_set_instruction, \
    extract_typename, DUMMY_INT_TYPEDECL


# Stateful compiler & ast node visitor
class Compiler(NodeVisitor):
    def __init__(self):
        self.functions = None
        self.current_function = None
        self.globals: dict = {}
        self.loops: list = []
        self.loop_end: int = 0
        self.vtmp_count: int = 0
        self.instructions: list = []
        self.if_structure_count: int = 0
        self.loop_structure_count: int = 0
        self.loop_stack: list = []
        # Used in short-circuit evaluation
        self.short_circuit_count: int = 0
        self.short_circuit_triggered: bool = False
        self.inside_branch_condition: bool = False
        self.tag_if_true: str = ""
        self.tag_if_false: str = ""
        self.tag_if_end: str = ""

        super().__init__()

    def reset(self):
        self.functions = {}
        self.current_function = None
        self.globals = {}
        self.vtmp_count = 0
        self.if_structure_count = 0
        self.loop_structure_count = 0
        self.short_circuit_count = 0
        self.loop_stack = []
        self.instructions = []
        # Used in short-circuit evaluation
        self.short_circuit_count = 0
        self.short_circuit_triggered = False
        self.inside_branch_condition = False
        self.tag_if_true = ""
        self.tag_if_false = ""
        self.tag_if_end = ""

    def compile(self, filename: str, use_cpp=True, cpp_args=None):
        self.reset()
        if cpp_args is None:
            cpp_args = []
        ast = parse_file(filename,
                         use_cpp=use_cpp,
                         cpp_args=["-I", get_include_path()] + cpp_args,
                         parser=GnuCParser())
        self.visit(ast)
        return self.instructions, self.functions

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
        if is_mlogev_temp_var(src_var) and self.peek().dest == src_var:
            self.peek().dest = dest_var
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
        self.vtmp_count += 1
        temp_var_name = F"__vtmp_{self.vtmp_count}"
        self.declare_variable(temp_var_name, var_type)
        if autodecorate:
            return self.decorate_variable(temp_var_name)
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

    def get_variable(self, var_name) -> tuple:
        result = None
        if self.current_function is not None:
            result = self.current_function.local_vars.get(var_name, None)
        if result is None:
            result = self.globals.get(var_name, None)
        return result, self.decorate_variable(var_name)

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
            tmp_var = self.create_temp_variable(dst_typedecl, True)
            self.push(Quadruple("cvtf64_i32", src_var, "", tmp_var))
            return tmp_var
        return src_var

    def create_loop(self):
        current_loop = self.loop_structure_count
        self.loop_structure_count += 1
        self.loop_stack.append(current_loop)
        label_prefix = f"__MLOGEV_LOOP_{current_loop}"
        start_label = f"{label_prefix}_START_"
        cont_label = f"{label_prefix}_CONT_"
        end_label = f"{label_prefix}_END_"
        return current_loop, start_label, cont_label, end_label

    def start_short_circuit_evaluation(self, tag_if_true="", tag_if_false=""):
        self.short_circuit_count += 1
        self.short_circuit_triggered = False
        if tag_if_true == "":
            prefix = f"__MLOGEV_SCE_{self.short_circuit_count}"
            self.tag_if_true = f"{prefix}_IFTRUE_"
            self.tag_if_false = f"{prefix}_IFFALSE_"
            self.tag_if_end = f"{prefix}_END_"
        else:
            self.tag_if_true = tag_if_true
            self.tag_if_false = tag_if_false
        self.inside_branch_condition = True

    def end_short_circuit_evaluation(self):
        self.inside_branch_condition = False

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
            self.current_function = Function(func_name, func_decl.type, params, dict(params), [])

        # self.function_locals = self.current_function.local_vars
        self.functions[func_name] = self.current_function

        self.push(Quadruple("__funcbegin", func_name, ""))
        self.visit(node.body)
        self.push(Quadruple("__funcend", func_name, ""))

        self.current_function = None
        # self.function_locals = {}

    def visit_Decl(self, node):
        if isinstance(node.type, TypeDecl):
            var_name = node.name
            # Keep TypeDecl, for further Struct/Pointer support
            var_type = node.type
            self.declare_variable(var_name, var_type)
            decorated_name = self.decorate_variable(var_name)
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
            self.functions[node.name] = Function(node.name, func_decl.type, params, dict(params), [])
            return
        if isinstance(node.type, Struct):
            if node.type.name != "MlogObject":
                raise NotImplementedError(node)
            node.show()
            return
        if isinstance(node.type, PtrDecl):
            # raise NotImplementedError("Pointers are NOT supported in mlog target", node)
            # node.show()
            return
        if isinstance(node.type, Enum):
            raise NotImplementedError(node)
        raise NotImplementedError(node)

    def visit_Assignment(self, node):
        # lvalue_decorated = self.decorate_variable(node.lvalue.name)
        lvalue_typedecl, lvalue_decorated = self.get_variable(node.lvalue.name)
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
        if extract_typename(result_typedecl) == extract_typename(lvalue_typedecl):
            self.push(Quadruple(inst, lvalue_decorated, rvalue, lvalue_decorated))
            return lvalue_typedecl, lvalue_decorated

        temp_var = self.create_temp_variable(result_typedecl, True)
        self.push(Quadruple(inst, lvalue_decorated, rvalue, temp_var))
        temp_after_cast = self.static_cast(temp_var, result_typedecl, lvalue_typedecl)
        self.heuristic_assign(temp_after_cast, lvalue_decorated, lvalue_typedecl)
        return lvalue_typedecl, lvalue_decorated

    # Return (type, value)
    def visit_Constant(self, node):
        if extract_typename(node.type) in ("double", "float"):
            value = str(float(node.value))
            return node.type, value
        return node.type, node.value

    def visit_ID(self, node):
        # Reserved for Extended Asm in functions
        if self.current_function is not None \
                and node.name == "__mlogev_function_return_value__":
            return self.current_function.result_type, f"result@{self.current_function.name}"
        # decorated_name = self.decorate_variable(node.name)
        var_typedecl, decorated_name = self.get_variable(node.name)
        return var_typedecl, decorated_name

    def visit_Cast(self, node):
        src_typedecl, src_var = self.visit(node.expr)
        result_var = self.static_cast(src_var, src_typedecl, node.to_type.type)
        return node.to_type.type, result_var

    # May be generated by comma operators
    def visit_ExprList(self, node):
        var_typedecl = None
        name_or_value = None
        for child in node:
            var_typedecl, name_or_value = self.visit(child)
        return var_typedecl, name_or_value

    def visit_BinaryOp(self, node):
        left_typedecl, left_var = self.visit(node.left)
        # Short-circuit environment created in visit_Assignment
        if_true, if_false = "", ""
        if self.inside_branch_condition:
            if_true = self.tag_if_true
            if_false = self.tag_if_false
        # Short-circuit evaluation
        if node.op in ("&&", "||"):
            self.short_circuit_triggered = True
            if node.op == "&&":
                self.push(Quadruple("ifnot", left_var, "false", if_false, relop="!="))
            else:
                self.push(Quadruple("if", left_var, "false", if_true, relop="!="))

        right_typedecl, right_var = self.visit(node.right)
        if node.op in ("&&", "||"):
            # TODO: is pythonic boolean right?
            return right_typedecl, right_var
        # END Short-circuit evaluation

        # TODO: implicit conversion?
        # Assume mlog arch does NOT require explicit int->double conversion
        result_typedecl, inst = choose_binaryop_instruction(
            node.op, left_typedecl, right_typedecl
        )
        temp_var = self.create_temp_variable(result_typedecl, True)
        self.push(Quadruple(inst, left_var, right_var, temp_var))
        return result_typedecl, temp_var

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

    def visit_If(self, node):
        label_prefix = f"__MLOGEV_IFELSE_{self.if_structure_count}"
        iftrue_label = f"{label_prefix}_IFTRUE_"
        iffalse_label = f"{label_prefix}_IFFALSE_"
        end_label = f"{label_prefix}_END_"
        self.if_structure_count += 1

        dest_label = end_label if node.iffalse is None else iffalse_label
        # Omit typedecl: it is always int / bool
        self.start_short_circuit_evaluation(iftrue_label, dest_label)
        _, cond_var = self.visit(node.cond)
        self.end_short_circuit_evaluation()

        # mlog has a builtin constant "false" == 0
        # optimizer will optimize this `cond_var != false` pattern
        self.push(Quadruple("ifnot", cond_var, "false", dest_label, relop="!="))
        self.push(Quadruple("label", iftrue_label))
        self.visit(node.iftrue)

        if node.iffalse is not None:
            self.push(Quadruple("goto", end_label))
            self.push(Quadruple("label", iffalse_label))
            self.visit(node.iffalse)
        self.push(Quadruple("label", end_label))

    def visit_For(self, node):
        current_loop, start_label, cont_label, end_label = \
            self.create_loop()
        afterinit_label = f"__MLOGEV_LOOP_{current_loop}_AFTERINIT_"

        if node.init is not None:
            self.visit(node.init)
        self.push(Quadruple("goto", afterinit_label))
        self.push(Quadruple("label", start_label))
        if node.stmt is not None:
            self.visit(node.stmt)
        self.push(Quadruple("label", cont_label))
        if node.next is not None:
            self.visit(node.next)
        self.push(Quadruple("label", afterinit_label))
        _, cond_var = self.visit(node.cond)
        self.push(Quadruple("if", cond_var, "false", start_label, relop="!="))
        self.push(Quadruple("label", end_label))

        self.loop_stack.pop()

    def visit_DoWhile(self, node):
        current_loop, start_label, cont_label, end_label = \
            self.create_loop()

        self.push(Quadruple("label", start_label))
        self.visit(node.stmt)
        self.push(Quadruple("label", cont_label))
        _, cond_var = self.visit(node.cond)
        self.push(Quadruple("if", cond_var, "false", start_label, relop="!="))
        self.push(Quadruple("label", end_label))

        self.loop_stack.pop()

    def visit_While(self, node):
        current_loop, start_label, cont_label, end_label = \
            self.create_loop()

        self.push(Quadruple("goto", cont_label))
        self.push(Quadruple("label", start_label))
        self.visit(node.stmt)
        self.push(Quadruple("label", cont_label))
        _, cond_var = self.visit(node.cond)
        self.push(Quadruple("if", cond_var, "false", start_label, relop="!="))
        self.push(Quadruple("label", end_label))

        self.loop_stack.pop()

    def visit_Label(self, node):
        self.push(Quadruple("label", node.name))
        self.visit(node.stmt)

    def visit_Goto(self, node):
        self.push(Quadruple("goto", node.name))

    def visit_Break(self, node):
        current_loop = self.loop_stack[-1]
        end_label = f"__MLOGEV_LOOP_{current_loop}_CONT_"
        self.push(Quadruple("goto", end_label))

    def visit_Continue(self, node):
        current_loop = self.loop_stack[-1]
        cont_label = f"__MLOGEV_LOOP_{current_loop}_CONT_"
        self.push(Quadruple("goto", cont_label))

    def visit_Return(self, node):
        function_name = self.current_function.name
        if node.expr is not None:
            r_typedecl, r_varname = self.visit(node.expr)
            result_typedecl = self.current_function.result_type
            result = r_varname
            if extract_typename(r_typedecl) \
                    != extract_typename(result_typedecl):
                result = self.static_cast(r_varname, r_typedecl, result_typedecl)

            dest = f"result@{function_name}"
            self.heuristic_assign(result, dest, result_typedecl)
        self.push(Quadruple("__return", function_name))

    def visit_FuncCall(self, node):
        function_name = node.name.name
        args = node.args or []
        func = self.functions.get(function_name, None)
        if func is None:
            raise ValueError(f"{function_name} is not a function (or not declared)")
        # if len(func.params) != len(args):
        #    raise ValueError(f"{function_name} expect {len(func.params)} params, got {len(args)}")
        for param_decl, arg in zip(func.params, args):
            param_realname = f"_{param_decl[0]}@{function_name}"
            arg_typedecl, arg_varname = self.visit(arg)
            real_argument = arg_varname
            param_type = extract_typename(param_decl[1])
            if extract_typename(arg_typedecl) != param_type:
                real_argument = self.static_cast(arg_varname, arg_typedecl, param_decl[1])
            self.heuristic_assign(real_argument, param_realname, param_decl[1])
        self.push(Quadruple("__call", function_name))
        # Assume a function returns something
        return func.result_type, f"result@{function_name}"

    def visit_Asm(self, node):
        result_ir = Quadruple("asm")
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


def extract_asm_operand(operand):
    # FuncCall -> name(Constant)
    constraints = operand.name.value
    # FuncCall -> args(ExprList) -> exprs[0]
    expr = operand.args.exprs[0]
    return constraints, expr


def is_mlogev_temp_var(varname):
    return varname.startswith("__vtmp_") or varname.startswith("___vtmp_")


def get_include_path():
    if os.name == "posix":
        return sysconfig.get_path("include", "posix_user")
    elif os.name == "nt":
        return sysconfig.get_path("include", "nt")
    else:
        raise ValueError(f"Unknown OS {os.name}")
