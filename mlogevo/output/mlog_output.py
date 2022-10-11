#!/usr/bin/python3
from ..intermediate.ir_quadruple import NOARG_INSTRUCTIONS, \
        I1_INSTRUCTIONS, I1O1_INSTRUCTIONS, \
        I2O1_INSTRUCTIONS, Quadruple

from .mlog_instructions import \
    mlog_set, mlog_label, mlog_jump_always, \
    mlog_jump_if, mlog_jump_ifnot, \
    mlog_setpc, mlog_rjump, \
    mlog_add, mlog_sub, mlog_mul, mlog_div, \
    mlog_idiv, mlog_mod, \
    mlog_floor, mlog_ceil, mlog_minus, \
    mlog_and, mlog_or, mlog_xor, \
    mlog_shl, mlog_shr, mlog_flip, \
    mlog_call, mlog_return, \
    mlog_noop

class IRtoMlogCompiler:
    def __init__(self, strict_32bit=False, keep_labels=False):
        self.strict_32bit = strict_32bit
        self.keep_labels = keep_labels
        self.registry = {}
        self.register_instructions()

    def register_instructions(self):
        wrapped_and = lambda src1, src2, dest: mlog_and(src1, src2, dest, self.strict_32bit)
        wrapped_or = lambda src1, src2, dest: mlog_or(src1, src2, dest, self.strict_32bit)
        wrapped_xor = lambda src1, src2, dest: mlog_xor(src1, src2, dest, self.strict_32bit)
        wrapped_shl = lambda src1, src2, dest: mlog_shl(src1, src2, dest, self.strict_32bit)
        wrapped_shr = lambda src1, src2, dest: mlog_shr(src1, src2, dest, self.strict_32bit)
        wrapped_flip = lambda src1, src2, dest: mlog_flip(src1, src2, dest, self.strict_32bit)
        self.registry["setl"] = self.registry["fset"] = mlog_set
        self.registry["label"] = mlog_label
        self.registry["setpc"] = mlog_setpc
        self.registry["rjump"] = mlog_rjump
        self.registry["addl"] = self.registry["fadd"] = mlog_add
        self.registry["subl"] = self.registry["fsub"] = mlog_sub
        self.registry["mull"] = self.registry["fmul"] = mlog_mul
        self.registry["fdiv"] = mlog_div
        self.registry["divl"] = mlog_idiv
        self.registry["reml"] = mlog_mod
        self.registry["ffloor"] = mlog_floor
        self.registry["fceil"] = mlog_ceil
        self.registry["minusl"] = self.registry["fminus"] = mlog_ceil
        self.registry["andl"] = wrapped_and
        self.registry["orl"] = wrapped_or
        self.registry["xorl"] = wrapped_xor
        self.registry["notl"] = wrapped_flip
        self.registry["lshl"] = wrapped_shl
        self.registry["rshl"] = wrapped_shr
        self.registry["noop"] = mlog_noop
        self.registry["__funcbegin"] = mlog_label
        self.registry["__funcend"] = lambda src1 : []
        self.registry["__call"] = mlog_call
        self.registry["__return"] = mlog_return

    def strip_labels(self, mlog_list) -> list[str]:
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

    def compile(self, ir_list) -> str:
        results = []
        for quadruple in ir_list:
            results.extend(self.convert_single_quadruple(quadruple))
        if not self.keep_labels:
            results = self.strip_labels(results)
        return "\n".join(results)

    def convert_single_quadruple(self, quadruple: Quadruple) -> list[str]:
        instruction = quadruple.instruction
        src1, src2, dest = quadruple.src1, quadruple.src2, quadruple.dest
        if instruction == "asm":
            return quadruple.raw_instructions
        if instruction in ("if", "ifnot"):
            jump_function = mlog_jump_if if quadruple.instruction == "if" else mlog_jump_ifnot
            relop = quadruple.relop
            return jump_function(src1, relop, src2, dest)
        # TODO: raise an error if instruction is unknown
        handler = self.registry[instruction]
        if instruction in NOARG_INSTRUCTIONS:
            return handler()
        if instruction in I1_INSTRUCTIONS:
            return handler(src1)
        if instruction in I1O1_INSTRUCTIONS:
            return handler(src1, dest)
        if instruction in I2O1_INSTRUCTIONS:
            return handler(src1, src2, dest)
        # TODO: raise an error
        return []

if __name__ == "__main__":
    import sys
    from ..intermediate.quadruple_from_text import TextQuadrupleParser
    parser = TextQuadrupleParser()
    result = parser.parse(sys.stdin.readlines())
    compiler = IRtoMlogCompiler(strict_32bit=False, keep_labels=False)
    print(compiler.compile(result))
