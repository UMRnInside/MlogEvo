from ..intermediate.ir_quadruple import Quadruple
from ..output import AbstractIRConverter
from ..output.mlog_output import IRtoMlogConverter
from ..output.ir_output import IRDumper

from .asm_template import mlog_expand_asm_template
from .basic_block import get_basic_blocks
from ..optimizer import append_optimizers


def dump_basic_blocks(name, blocks):
    n = len(blocks.keys())
    print("Function", name)
    for i in range(n):
        block = blocks[i]
        print(f"BLK {i}, may jump to {block.jump_destination}"
              f"{', may continue' if block.will_continue else ''}")
        for ir in block.instructions:
            print(ir.dump())
        print()
    print()


class Backend:
    def __init__(self):
        # function_optimizers: work on the whole function
        self.function_optimizers = []
        self.basic_block_optimizers = []
        self.block_graph_optimizers = []
        self.asm_template_handler = None
        self.output_component: AbstractIRConverter = None

    def compile(self, frontend_result, dump_blocks=False) -> str:
        inits, functions = frontend_result
        for (name, body) in functions.items():
            for optimizer in self.function_optimizers:
                optimizer(body)

            function_basic_blocks = get_basic_blocks(body.instructions)
            for (block_id, block) in function_basic_blocks.items():
                for optimizer in self.basic_block_optimizers:
                    optimizer(block, functions)

            for optimizer in self.block_graph_optimizers:
                optimizer(function_basic_blocks)
            n = len(function_basic_blocks.keys())
            function_ir_list = []

            for i in range(n):
                function_ir_list.extend(function_basic_blocks[i].instructions)
            body.instructions = function_ir_list

            if dump_blocks:
                dump_basic_blocks(name, function_basic_blocks)

        ir_list = inits[:] + functions["main"].instructions
        # make main() the first function
        for (name, body) in functions.items():
            if name == "main": continue
            ir_list.extend(body.instructions)
        self.convert_asm(ir_list)
        return self.output_component.convert(ir_list)

    def convert_asm(self, ir_list):
        asm_blocks = 0
        for i in range(len(ir_list)):
            if ir_list[i].instruction != "asm":
                continue
            ir_list[i].raw_instructions = self.asm_template_handler(ir_list[i], asm_blocks)
            asm_blocks += 1
        return ir_list


def make_backend(arch="mlog", target="mlog",
                 machine_independents=None,
                 machine_dependents=None,
                 optimize_level=0):
    """make_backend(arch='mlog', target='mlog', machine_independants={}, machine_dependants={})
    """
    if machine_independents is None:
        machine_independents = []
    if machine_dependents is None:
        machine_dependents = []

    backend = Backend()
    if arch == "mlog":
        backend.asm_template_handler = mlog_expand_asm_template
    if target == "mlog":
        backend.output_component = IRtoMlogConverter(
            strict_32bit="strict-32bit" in machine_dependents
        )
    elif target == "mlogev_ir":
        backend.output_component = IRDumper()

    append_optimizers(backend, machine_dependents, machine_independents, optimize_level)

    return backend
