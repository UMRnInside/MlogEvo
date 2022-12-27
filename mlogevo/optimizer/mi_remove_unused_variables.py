from typing import Set
from ..intermediate.function import Function
from ..intermediate.ir_quadruple import I1_INSTRUCTIONS, Quadruple
from .optimizer_registry import register_optimizer


# run AFTER LCSE
@register_optimizer(
    name="remove-unused-variables",
    target="function",
    is_machine_dependent=False,
    rank=20,
    optimize_level=1
)
def remove_unused_variables(func: Function) -> Function:
    insts = func.instructions
    referred_variables = set()
    referred_variables.add("")

    for inst in insts:
        if inst in ("goto", "__funcbegin", "__funcend"):
            continue
        if inst.instruction.startswith("decl_"):
            continue
        referred_variables.add(inst.src1)
        referred_variables.add(inst.src2)
        for var in inst.input_vars:
            referred_variables.add(var)

    result_insts = []
    for inst in insts:
        if inst.instruction.startswith("decl_") and should_remove_decl(inst, func.name, referred_variables):
            continue
        if inst.dest.endswith(f"@{func.name}") and should_remove_normal(inst, func.name, referred_variables):
            continue
        result_insts.append(inst)
    func.instructions = result_insts
    return func


def should_remove_decl(inst: Quadruple, function_name: str, referred: Set):
    return inst.src1.endswith(f"@{function_name}") \
        and not inst.src1.startswith("result@") \
        and inst.src1 not in referred


def should_remove_normal(inst: Quadruple, function_name: str, referred: Set):
    return inst.dest.endswith(f"@{function_name}") \
        and not inst.dest.startswith("result@") \
        and inst.dest not in referred