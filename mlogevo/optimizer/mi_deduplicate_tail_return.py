from ..intermediate.function import Function
from .optimizer_registry import register_optimizer

# Machine-independant
# Input: whole function
@register_optimizer(
    name="deduplicate-tail-return",
    target="function",
    is_machine_dependant=False
)
def deduplicate_tail_return(func: Function) -> Function:
    return_ir = func.instructions[-1]
    if return_ir.instruction != "__funcend":
        return func
    func.instructions.pop()
    while len(func.instructions) > 0 \
            and func.instructions[-1].instruction == "__return":
        func.instructions.pop()
    func.instructions.append(return_ir)
    return func
