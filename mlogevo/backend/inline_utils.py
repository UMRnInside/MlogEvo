from typing import Iterable, Tuple, List, Dict
from copy import copy

from ..intermediate import Quadruple
from ..intermediate.ir_quadruple import NO_INPUT_INSTRUCTIONS
from ..intermediate.function import Function


def should_inline(function: Function, arch="mlog") -> bool:
    if function.name == "main":
        return False
    if "inline" not in function.attributes:
        return False
    if "always_inline" in function.attributes:
        return True
    if arch == "mlog":
        return mlog_should_inline(function)
    return False


def mlog_should_inline(function: Function) -> bool:
    size = 0
    for inst in function.instructions:
        if inst.instruction in ("__funcbegin", "__funcend"):
            continue
        if inst.instruction == "__call":
            # TODO: consider inline functions that calls other functions
            return False
        if inst.instruction in ("label",):
            # size += 0
            continue
        if inst.instruction == "asm":
            size += len(inst.raw_instructions)
            continue
        size += 1
    # __call:2, __return:1, set return value: 1
    return size <= 16


def filter_inlineable_functions(functions: Iterable[Function], arch: str = "mlog") \
        -> Tuple[Dict[str, Function], Dict[str, Function]]:
    inline_functions: Dict[str, Function] = {}
    common_functions: Dict[str, Function] = {}
    for function in functions:
        if should_inline(function, arch):
            inline_functions[function.name] = function
        else:
            common_functions[function.name] = function
    return inline_functions, common_functions


def redirect_variable(ir: Quadruple, from_var: str, to_var: str) -> Quadruple:
    if from_var == to_var:
        return ir
    if ir.instruction.startswith("decl_") or ir.instruction in NO_INPUT_INSTRUCTIONS:
        return ir

    if ir.src1 == from_var:
        ir.src1 = to_var
    if ir.src2 == from_var:
        ir.src2 = to_var
    if ir.dest == from_var:
        ir.dest = to_var

    # Avoid modifying original input_vars and output_vars
    input_vars = []
    output_vars = []
    for v in ir.input_vars:
        input_vars.append(v if v != from_var else to_var)
    for v in ir.output_vars:
        output_vars.append(v if v != from_var else to_var)
    ir.input_vars = input_vars
    ir.output_vars = output_vars
    return ir


def inline_calls(common_function_name: str,
                 common_function_body: List[Quadruple],
                 inline_functions: Dict[str, Function],) -> List[Quadruple]:
    result_irs: List[Quadruple] = []
    ctr = 0
    last_result_assignment: Dict[str, str] = {}
    # A reference
    last_assignment_ir: Dict[str, Quadruple] = {}
    for ir in reversed(common_function_body):
        if ir.instruction.startswith("set_") and ir.src1.startswith("result@"):
            last_result_assignment[ir.src1] = ir.dest
            last_assignment_ir[ir.src1] = ir
            result_irs.append(ir)
            continue
        if ir.instruction != "__call":
            result_irs.append(ir)
            continue
        if ir.src1 not in inline_functions.keys():
            result_irs.append(ir)
            continue
        ctr += 1
        inlined_target = inline_functions[ir.src1]
        inlined_body = inlined_target.instructions
        result_var = f"result@{inlined_target.name}"
        assigned_to_var = last_result_assignment.get(result_var, result_var)
        inlined_block = []
        return_jump = f"__MLOGEV_INLINE_CALL_{inlined_target.name}_{common_function_name}_{ctr}__"
        for inst in inlined_body:
            if inst.instruction in ("__funcbegin", "__funcend"):
                continue
            if inst.instruction == "__return":
                inlined_block.append(Quadruple("goto", return_jump))
                continue
            inlined_block.append(redirect_variable(copy(inst), result_var, assigned_to_var))
        inlined_block.append(Quadruple("label", return_jump))
        #print("\n".join((v.dump() for v in inlined_block)))
        inlined_block.reverse()
        result_irs.extend(inlined_block)
        if assigned_to_var != result_var:
            last_assignment_ir[result_var].instruction = "ELIMINATED"
            del last_result_assignment[result_var]
            del last_assignment_ir[result_var]

    return [i for i in reversed(result_irs) if i.instruction != "ELIMINATED"]
