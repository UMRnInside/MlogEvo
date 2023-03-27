from dataclasses import dataclass, field
from typing import List, Dict, Set
import sysconfig
import os
# for string constants

from ..intermediate import Quadruple
from .compiler_sketch import choose_binaryop_instruction
from .components.branch_support import BranchSupport


# Stateful compiler & ast node visitor
class Compiler(BranchSupport):
    def __init__(self):
        super().__init__()

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
                self.push(Quadruple("ifnot", left_var, "false", if_false, relop="ne_i32"))
            else:
                self.push(Quadruple("if", left_var, "false", if_true, relop="ne_i32"))

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