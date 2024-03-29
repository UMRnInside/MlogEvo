from typing import Iterable, Dict, Set
from ..intermediate.ir_quadruple import Quadruple, COMPARISONS
from ..intermediate.function import Function
from ..output import AbstractIRConverter
from ..output.mlog_output import IRtoMlogConverter
from ..output.ir_output import IRDumper

from .asm_template import mlog_expand_asm_template
from .basic_block import get_basic_blocks
from .inline_utils import filter_inlineable_functions, inline_calls
from ..optimizer import append_optimizers
from ..frontend.abstract_compiler import FrontendResult


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


def read_variable_types(ir_list: Iterable[Quadruple], result: Dict[str, str]):
    for ir in ir_list:
        if ir.dest == "" or ir.instruction.startswith("__"):
            continue
        if ir.instruction in ("if", "ifnot"):
            continue
        if ir.instruction in COMPARISONS:
            result[ir.dest] = "i32"
        tokens = ir.instruction.split("_")
        result[ir.dest] = tokens[-1]


class Backend:
    def __init__(self, arch, target):
        self.arch = arch
        self.target = target
        # function_optimizers: work on the whole function
        self.mi_optimizers = []
        self.asm_template_handler = None
        self.output_component: AbstractIRConverter = None

    def compile(self, frontend_result: FrontendResult, dump_blocks=False) -> str:
        inits = frontend_result.global_instructions
        all_functions = frontend_result.functions

        variable_types: Dict[str, str] = {}
        read_variable_types(inits, variable_types)
        for function in all_functions.values():
            read_variable_types(function.instructions, variable_types)
        inline_functions, common_functions = filter_inlineable_functions(all_functions.values())

        for function in inline_functions.values():
            self.run_optimize_pass(function, all_functions, variable_types, dump_blocks)
        for function in common_functions.values():
            function.instructions = inline_calls(function.name, function.instructions, inline_functions)
            self.run_optimize_pass(function, all_functions, variable_types, dump_blocks)

        ir_list = inits[:]
        # make main() the first function
        if "main" in common_functions.keys():
            ir_list += common_functions["main"].instructions
        for (name, body) in common_functions.items():
            if name == "main": continue
            ir_list.extend(body.instructions)
        if self.target != "mlogev_ir":
            self.convert_asm(ir_list)
        return self.output_component.convert(ir_list)

    def run_optimize_pass(self, function: Function, all_functions, variable_types: Dict[str, str], dump_blocks=False):
        for optimizer_triplet in self.mi_optimizers:
            optimizer, target, rank = optimizer_triplet
            if target == "function":
                optimizer(function)
            elif target == "basic_block":
                function_basic_blocks = get_basic_blocks(function.instructions)
                block_id_list = sorted(list(function_basic_blocks.keys()))
                for block_id in block_id_list:
                    block = function_basic_blocks[block_id]
                    optimizer(block, function.name, all_functions, variable_types)
                function_ir_list = []
                for i in block_id_list:
                    function_ir_list.extend(function_basic_blocks[i].instructions)
                function.instructions = function_ir_list

        if dump_blocks:
            function_basic_blocks = get_basic_blocks(function.instructions)
            dump_basic_blocks(function.name, function_basic_blocks)
        return function

    def convert_asm(self, ir_list):
        asm_blocks = 0
        for i in range(len(ir_list)):
            if ir_list[i].instruction not in ("asm", "asm_volatile"):
                continue
            ir_list[i].raw_instructions = self.asm_template_handler(ir_list[i], asm_blocks)
            asm_blocks += 1
        return ir_list


def make_backend(arch="mlog", target="mlog",
                 machine_independents=None,
                 machine_dependents=None,
                 optimize_level=0) -> Backend:
    """make_backend(arch='mlog', target='mlog', machine_independents={}, machine_dependents={})
    """
    if machine_independents is None:
        machine_independents = []
    if machine_dependents is None:
        machine_dependents = []

    backend = Backend(arch, target)
    if arch == "mlog":
        backend.asm_template_handler = mlog_expand_asm_template
    if target == "mlog":
        backend.output_component = IRtoMlogConverter(
            strict_32bit="strict-32bit" in machine_dependents,
            keep_labels="keep-labels" in machine_dependents,
        )
    elif target == "mlogev_ir":
        backend.output_component = IRDumper()
    append_optimizers(backend, machine_dependents, machine_independents, optimize_level)
    return backend
