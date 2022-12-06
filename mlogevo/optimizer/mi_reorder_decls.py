from ..intermediate.function import Function
from .optimizer_registry import register_optimizer


@register_optimizer(
    name="reorder-decls",
    target="function",
    is_machine_dependent=False,
    rank=2,
    optimize_level=0
)
def reorder_decls(func: Function) -> Function:
    start = func.instructions[0]
    decls = []
    body = []
    for ir in func.instructions[1:-1]:
        if ir.instruction.startswith("decl_"):
            decls.append(ir)
        else:
            body.append(ir)
    end = func.instructions[-1]
    decls.sort(key=lambda ir: ir.instruction)
    func.instructions = [start, ] + decls + body + [end, ]
    return func
