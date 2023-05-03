from ..intermediate.function import Function
from .optimizer_registry import register_optimizer


@register_optimizer(
    name="remove-unused-decls",
    target="function",
    is_machine_dependent=False,
    rank=98,
    optimize_level=0
)
def remove_decls(func: Function) -> Function:
    start = func.instructions[0]
    decls = []
    referred = set()
    body = []
    for ir in func.instructions[1:-1]:
        if ir.instruction.startswith("decl_"):
            decls.append(ir)
            continue
        body.append(ir)
        referred.add(ir.src1)
        referred.add(ir.src2)
        referred.add(ir.dest)
        for var in ir.input_vars:
            referred.add(var)
        for var in ir.output_vars:
            referred.add(var)
    end = func.instructions[-1]
    referred_decls = [x for x in decls if x.dest in referred or "argument" in x.src1]
    func.instructions = [start, ] + referred_decls + body + [end, ]
    return func
