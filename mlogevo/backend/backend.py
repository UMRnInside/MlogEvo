from ..intermediate.ir_quadruple import Quadruple

from ..output.mlog_output import IRtoMlogCompiler

class Backend:
    def __init__(self):
        self.optimizers = []
        self.outputter = None

    def compile(self, ir_list) -> str:
        for optimizer in self.optimizers:
            ir_list = optimizer(ir_list)
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
    return backend

