from typing import List
from ...intermediate import Quadruple
from ...intermediate.ir_quadruple import COMPARISONS
from ..compiler_sketch import CompilerSketch

class BranchSupport(CompilerSketch):
    def __init__(self):
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

    def create_loop(self):
        current_loop = self.loop_structure_count
        self.loop_structure_count += 1
        self.loop_stack.append(current_loop)
        label_prefix = f"__MLOGEV_LOOP_{current_loop}"
        start_label = f"{label_prefix}_START_"
        cont_label = f"{label_prefix}_CONT_"
        end_label = f"{label_prefix}_END_"
        return current_loop, start_label, cont_label, end_label

    def get_faster_conditional_jump(self):
        if self.current_function is None:
            return
        curr_instructions: List[Quadruple] = self.current_function.instructions
        if len(curr_instructions) < 2:
            return
        jumper = curr_instructions[-1]
        cond_ir = curr_instructions[-2]
        if jumper.instruction not in ("if", "ifnot"):
            return
        if cond_ir.instruction not in COMPARISONS:
            return
        if jumper.src1 != cond_ir.dest:
            return
        curr_instructions.pop()
        curr_instructions.pop()
        tmpvar = cond_ir.dest
        self.remove_temp_variable(tmpvar)

        jumper.src1 = cond_ir.src1
        jumper.src2 = cond_ir.src2
        # jumper.relop = COMPARISON_TO_BINARY_OP[cond_ir.instruction]
        jumper.relop = cond_ir.instruction
        curr_instructions.append(jumper)

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
        self.push(Quadruple("ifnot", cond_var, "false", dest_label, relop="ne_i32"))
        self.get_faster_conditional_jump()

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
        self.push(Quadruple("if", cond_var, "false", start_label, relop="ne_i32"))
        self.get_faster_conditional_jump()
        self.push(Quadruple("label", end_label))

        self.loop_stack.pop()

    def visit_DoWhile(self, node):
        current_loop, start_label, cont_label, end_label = \
            self.create_loop()

        self.push(Quadruple("label", start_label))
        self.visit(node.stmt)
        self.push(Quadruple("label", cont_label))
        _, cond_var = self.visit(node.cond)
        self.push(Quadruple("if", cond_var, "false", start_label, relop="ne_i32"))
        self.get_faster_conditional_jump()
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
        self.push(Quadruple("if", cond_var, "false", start_label, relop="ne_i32"))
        self.get_faster_conditional_jump()
        self.push(Quadruple("label", end_label))

        self.loop_stack.pop()

    def visit_Break(self, node):
        current_loop = self.loop_stack[-1]
        end_label = f"__MLOGEV_LOOP_{current_loop}_CONT_"
        self.push(Quadruple("goto", end_label))

    def visit_Continue(self, node):
        current_loop = self.loop_stack[-1]
        cont_label = f"__MLOGEV_LOOP_{current_loop}_CONT_"
        self.push(Quadruple("goto", cont_label))