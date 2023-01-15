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
    referred_variables = {"", }
    involved_functions = {func.name, }

    for inst in insts:
        if inst in ("goto", "__funcbegin", "__funcend"):
            continue
        if inst.instruction.startswith("decl_"):
            continue
        # TODO: call vs __call
        if inst.instruction == "__call":
            involved_functions.add(inst.src1)

        referred_variables.add(inst.src1)
        referred_variables.add(inst.src2)
        for var in inst.input_vars:
            referred_variables.add(var)

    result_insts = []
    for inst in insts:
        if inst.instruction.startswith("decl_") \
                and should_remove_name(inst.src1, func.name, referred_variables, involved_functions):
            continue
        if inst.dest.endswith(f"@{func.name}") \
                and should_remove_name(inst.dest, func.name, referred_variables, involved_functions):
            continue
        result_insts.append(inst)
    func.instructions = result_insts
    return func


def should_remove_name(name: str, function_name: str, referred: Set, involved_functions: Set):
    if name in referred or "@" not in name or name.startswith("@"):
        return False
    function_scope = name.rsplit("@")[-1]
    if function_scope not in involved_functions:
        return True
    return function_scope == function_name and not name.startswith("result@")
