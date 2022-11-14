#!/usr/bin/python3
from typing import List

from .ir_quadruple import NOARG_INSTRUCTIONS, \
        I1_INSTRUCTIONS, I1O1_INSTRUCTIONS, \
        I2O1_INSTRUCTIONS, Quadruple

class TextQuadrupleParser:
    def __init__(self):
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
            if inst != "__asmend" and self.inside_asm_block:
                self.current_asm.raw_instructions.append(line)
                continue
            if inst == "__asmbegin" and not self.inside_asm_block:
                self.inside_asm_block = True
                self.current_asm = Quadruple("asm")
                self.current_asm.input_vars = tokens[2:]
                continue
            if inst == "__asmend":
                self.inside_asm_block = False
                self.current_asm.output_vars = tokens[2:]
                results.append(self.current_asm)
                continue

            if inst.startswith(":"):
                results.append(Quadruple("label", inst[1:], ""))
                continue
            if inst in NOARG_INSTRUCTIONS:
                results.append(Quadruple(inst))
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


if __name__ == "__main__":
    import sys
    parser = TextQuadrupleParser()
    result = parser.parse(sys.stdin.readlines())
    print(result)
