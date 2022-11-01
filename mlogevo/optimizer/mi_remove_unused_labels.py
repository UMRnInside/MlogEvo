from ..intermediate.function import Function
from .optimizer_registry import register_optimizer


@register_optimizer(
    name="remove-unused-labels",
    target="function",
    is_machine_dependent=False,
    rank=1,
    optimize_level=1
)
def remove_unused_labels(func: Function) -> Function:
    insts = func.instructions
    used_labels = set()
    # IR instructions that uses labels:
    # if, ifnot, goto
    # if, ifnot: label in dest
    # goto: label in src1
    for inst in insts:
        if inst.instruction in ("if", "ifnot"):
            used_labels.add(inst.dest)
        elif inst.instruction == "goto":
            used_labels.add(inst.src1)

    result_insts = []
    # label: name in src1
    for inst in insts:
        if inst.instruction != "label" or inst.src1 in used_labels:
            result_insts.append(inst)
    func.instructions = result_insts
    return func
