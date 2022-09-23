from dataclasses import dataclass, field

NOARG_INSTRUCTIONS = set([
    "noop",
])

I1_INSTRUCTIONS = set([
    "goto", "setpc", "rjump",
    "label",
    "__funcbegin", "__funcend", "__call", "__return",
])

I1O1_INSTRUCTIONS = set([
    "setl", "fset",
    "ffloor", "fceil",
    "minusl", "fminus",
    "notl",
])

I2O1_INSTRUCTIONS = set([
    "addl", "fadd",
    "mull", "fmul",
    "divl", "fdiv",
    "reml",
    "andl", "orl", "xorl",
    "lshl", "rshl"
])

@dataclass
class Quadruple:
    """Quadruple IR, dataclass format."""
    instruction: str
    src1: str = ""
    src2: str = ""
    dest: str = ""

    # For labels:
    # instruction = "label"
    # src1 = (label name)

    # For if and ifnot
    # src1 relop src2, jump to dest
    relop: str = ""

    # For asm, instruction name is "asm" (w/o quotes)
    input_vars: list[str] = field(default_factory=list)
    output_vars: list[str] = field(default_factory=list)
    raw_instructions: list[str] = field(default_factory=list)

    def dump(self) -> str:
        if self.instruction == "label":
            return F":{self.src1}"
        if self.instruction in NOARG_INSTRUCTIONS:
            return F"{self.instruction}"
        if self.instruction in I1_INSTRUCTIONS:
            return F"{self.instruction} {self.src1}"
        if self.instruction in I1O1_INSTRUCTIONS:
            return F"{self.instruction} {self.src1} {self.dest}"
        if self.instruction in I2O1_INSTRUCTIONS:
            return F"{self.instruction} {self.src1} {self.src2} {self.dest}"
        if self.instruction in ("if", "ifnot"):
            return F"{self.instruction} {self.src1} {self.relop} {self.src2} goto {self.dest}"
        # if self.instruction == "asm"
        asm_begin = " ".join(["__asmbegin", str(self.input_vars), ] + self.input_vars)
        asm_end = " ".join(["__asmend", str(self.output_vars), ] + self.output_vars)
        result = [asm_begin, ]
        result.extend(self.raw_instructions)
        result.append(asm_end)
        return "\n".join(result)

