from ..intermediate.ir_quadruple import Quadruple
from ..output.mlog_output import IRtoMlogCompiler
from .asm_template import mlog_expand_asm_template

class Backend:
    def __init__(self):
        self.optimizers = []
        self.asm_template_handler = None
        self.outputter = None

    def compile(self, ir_list) -> str:
        for optimizer in self.optimizers:
            ir_list = optimizer(ir_list)
        asm_blocks = 0
        for i in range(len(ir_list)):
            if ir_list[i].instruction != "asm":
                continue
            ir_list[i] = self.asm_template_handler(ir_list[i], asm_blocks)
            asm_blocks += 1
        return self.outputter.compile(ir_list)

def make_backend(arch="mlog", target="mlog", 
        machine_independants=dict(),
        machine_dependants=dict()):
    """make_backend(arch='mlog', target='mlog', machine_independants={}, machine_dependants={})
    """
    backend = Backend()
    if arch == "mlog" and target == "mlog":
        backend.outputter = IRtoMlogCompiler(
                strict_32bit=machine_dependants.get("strict-32bit", False))
        backend.asm_template_handler = mlog_expand_asm_template
    return backend

