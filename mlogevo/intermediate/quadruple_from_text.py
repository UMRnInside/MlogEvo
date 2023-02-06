#!/usr/bin/python3
from typing import List, Iterable

from .ir_quadruple import NOARG_INSTRUCTIONS, \
    O1_INSTRUCTIONS, I1_INSTRUCTIONS, I1O1_INSTRUCTIONS, \
    I2O1_INSTRUCTIONS, Quadruple
from .function import Function


class TextQuadrupleParser:
    def __init__(self):
        self.inside_asm_block: bool = False
        self.current_asm: Quadruple = Quadruple("asm")
        self.reset()

    def reset(self):
        self.inside_asm_block = False
        self.current_asm = Quadruple("asm")

    def parse(self, lines) -> List[Quadruple]:
        results = []
        for line in lines:
            tokens = line.split()
            if len(tokens) == 0:
                continue

            inst = tokens[0]
            if inst not in ("__asmend", "__asmvend") and self.inside_asm_block:
                self.current_asm.raw_instructions.append(line.strip())
                continue
            if inst in ("__asmbegin", "__asmvbegin") and not self.inside_asm_block:
                self.inside_asm_block = True
                self.current_asm = Quadruple("asm_volatile" if inst == "__asmvbegin" else "asm")
                self.current_asm.input_vars = tokens[2:]
                continue
            if inst in ("__asmend", "__asmvend"):
                self.inside_asm_block = False
                self.current_asm.output_vars = tokens[2:]
                continue

            if inst.startswith(":"):
                results.append(Quadruple("label", inst[1:], ""))
                continue
            if inst in NOARG_INSTRUCTIONS:
                results.append(Quadruple(inst))
                continue
            if inst in O1_INSTRUCTIONS:
                results.append(Quadruple(inst, dest=tokens[1]))
                continue
            if inst in I1_INSTRUCTIONS:
                results.append(Quadruple(inst, tokens[1]))
                continue
            if inst in I1O1_INSTRUCTIONS:
                results.append(Quadruple(inst, tokens[1], "", tokens[2]))
                continue
            if inst in I2O1_INSTRUCTIONS:
                results.append(Quadruple(inst, tokens[1], tokens[2], tokens[3]))
                continue
            if inst == "if" or inst == "ifnot":
                # There could be 2 patterns for <condition>:
                # x, or x > 42
                if len(tokens) == 6:
                    results.append(
                        Quadruple(inst, tokens[1], tokens[3], tokens[5], relop=tokens[2]) )
                elif len(tokens) == 4:
                    results.append(
                        Quadruple(inst, tokens[1], "", tokens[3], relop="") )
                continue
                
        return results


def extract_functions_from_ir(ir_list: Iterable[Quadruple]):
    current_function: Function = None
    init_irs = []
    functions = {}
    is_inside_function = False
    for ir in ir_list:
        if ir.instruction == "__funcbegin":
            # TODO: other attributes
            current_function = Function(
                name=ir.src1,
                result_type=None,
                params=None,
                local_vars=None,
                instructions=[],
                attributes=ir.dest.split(",")
            )
            current_function.instructions.append(ir)
            is_inside_function = True
        elif is_inside_function:
            current_function.instructions.append(ir)
            if ir.instruction == "__funcend":
                functions[current_function.name] = current_function
                is_inside_function = False
                current_function = None
        else:
            init_irs.append(ir)
    return init_irs, functions


if __name__ == "__main__":
    import sys
    parser = TextQuadrupleParser()
    result = parser.parse(sys.stdin.readlines())
    print(result)
