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
    "lshl", "rshl",
    "ltl", "flt",
    "gtl", "fgt",
    "lteql", "flteq",
    "gteql", "fgteq",
    "eql", "feq",
    "nel", "fne",
])

def test_parameter_type(param: str) -> str:
    """Test a parameter if it's a "immediate_integer", "immediate_float", "variable" or "invalid" """
    if type(param) is not str or len(param) == 0:
        return "invalid"
    if param[0].isalpha() or param[0] == '_':
        return "variable"

    # Test if param is base 10 or 16
    try:
        x = int(param, 10)
        return "immediate_integer"
    except ValueError:
        pass
    try:
        x = int(param, 16)
        return "immediate_integer"
    except ValueError:
        pass
    try:
        y = float(param)
        return "immediate_float"
    except:
        pass

    return "invalid"


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

    # Tell if src1 or src2 is immediate integer or float
    src1_type: str = "invalid"
    src2_type: str = "invalid"

    # For asm, instruction name is "asm" (w/o quotes)
    input_vars: list[str] = field(default_factory=list)
    output_vars: list[str] = field(default_factory=list)
    raw_instructions: list[str] = field(default_factory=list)

    @property
    def src1(self) -> str:
        return self._src1

    @property
    def src2(self) -> str:
        return self._src2

    @src1.setter
    def src1(self, value: str) -> None:
        self._src1 = value
        self.src1_type = test_parameter_type(self._src1)

    @src2.setter
    def src2(self, value: str) -> None:
        self._src2 = value
        self.src2_type = test_parameter_type(self._src2)

    def __post_init__(self):
        self.src1_type = test_parameter_type(self.src1)
        self.src2_type = test_parameter_type(self.src2)

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

