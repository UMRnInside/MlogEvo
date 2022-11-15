#!/usr/bin/python3
from typing import List

from ..intermediate.ir_quadruple import NOARG_INSTRUCTIONS, \
        I1_INSTRUCTIONS, I1O1_INSTRUCTIONS, \
        I2O1_INSTRUCTIONS, Quadruple
from .abstract_ir_converter import AbstractIRConverter
from .mlog_instructions import mlog_ir_registry


def strip_labels(mlog_list) -> List[str]:
    labels = {}
    results = []
    counter = 0
    for inst in mlog_list:
        if inst.endswith(":"):
            label_name = inst[:-1]
            labels[label_name] = counter
        elif len(inst.split()) == 0:
            pass
        else:
            counter += 1
            results.append(inst)
    for (line_no, inst) in enumerate(results):
        if inst.startswith("jump "):
            tokens = inst.split()
            tokens[1] = str( labels[tokens[1]] )
            results[line_no] = " ".join(tokens)
    return results


class IRtoMlogConverter(AbstractIRConverter):
    def __init__(self, strict_32bit=False, keep_labels=False):
        self.strict_32bit = strict_32bit
        self.keep_labels = keep_labels

    def convert(self, ir_list) -> str:
        results = []
        for quadruple in ir_list:
            results.extend(self.convert_single_quadruple(quadruple))
        if not self.keep_labels:
            results = strip_labels(results)
        return "\n".join(results)

    def convert_single_quadruple(self, quadruple: Quadruple) -> List[str]:
        instruction = quadruple.instruction
        src1, src2, dest = quadruple.src1, quadruple.src2, quadruple.dest
        if instruction == "asm":
            return quadruple.raw_instructions
        handler = mlog_ir_registry[instruction]
        if instruction in ("if", "ifnot"):
            relop = quadruple.relop
            return handler(src1, relop, src2, dest)
        # TODO: raise an error if instruction is unknown
        if instruction in NOARG_INSTRUCTIONS:
            return handler()
        if instruction in I1_INSTRUCTIONS:
            return handler(src1)
        if instruction in I1O1_INSTRUCTIONS:
            result = handler(src1, dest)
            if self.strict_32bit:
                result.append(f"op and {dest} {dest} 4294967295")
            return result
        if instruction in I2O1_INSTRUCTIONS:
            result = handler(src1, src2, dest)
            if self.strict_32bit:
                result.append(f"op and {dest} {dest} 4294967295")
            return result
        raise ValueError(f"Unrecognized IR: {repr(instruction)}")


if __name__ == "__main__":
    import sys
    from ..intermediate.quadruple_from_text import TextQuadrupleParser
    parser = TextQuadrupleParser()
    result = parser.parse(sys.stdin.readlines())
    compiler = IRtoMlogConverter(strict_32bit=False, keep_labels=False)
    print(compiler.convert(result))
