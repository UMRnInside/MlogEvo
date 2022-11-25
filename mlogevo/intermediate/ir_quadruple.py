from dataclasses import dataclass, field
from typing import List
import re

SUPPORTED_ARITHMETIC_TYPES = {
    "i32", "f64",
}
ASM_INSTRUCTIONS = {"asm", "asm_volatile"}
NOARG_INSTRUCTIONS = {
    "noop",
}
I1_INSTRUCTIONS = {
    "goto",
    "label",
    "__funcend", "__call", "__return",
}
I1O1_INSTRUCTIONS = {
    "set_obj",
    "cvtf64_i32", "cvti32_f64",
    # __funcbegin function_name attribute
    "__funcbegin",
}
I2O1_INSTRUCTIONS = set()
O1_INSTRUCTIONS = {"decl_obj", }
COMPARISONS = set()

CORE_I1O1_ITEMS = {
    "set", "minus",
}
CORE_I2O1_ITEMS = {
    "add", "sub", "mul", "div",
    "lt", "gt", "lteq", "gteq", "eq", "ne"
}
CORE_O1_ITEMS = {
    "decl",
}
CORE_COMPARISON_ITEMS = {
    "lt", "lteq", "gteq", "gt", "eq", "ne",
}
I32ONLY_I2O1_ITEMS = {
    "and", "or", "xor", "lsh", "rsh",
    "rem",
}
I32ONLY_I1O1_ITEMS = {
    "not",
}

for i in CORE_O1_ITEMS:
    for t in SUPPORTED_ARITHMETIC_TYPES:
        O1_INSTRUCTIONS.add(f"{i}_{t}")

for i in CORE_COMPARISON_ITEMS:
    for t in SUPPORTED_ARITHMETIC_TYPES:
        COMPARISONS.add(f"{i}_{t}")

for i in CORE_I1O1_ITEMS:
    for t in SUPPORTED_ARITHMETIC_TYPES:
        I1O1_INSTRUCTIONS.add(f"{i}_{t}")

for i in CORE_I2O1_ITEMS:
    for t in SUPPORTED_ARITHMETIC_TYPES:
        I2O1_INSTRUCTIONS.add(f"{i}_{t}")

for i in I32ONLY_I1O1_ITEMS:
    I1O1_INSTRUCTIONS.add(f"{i}_i32")

for i in I32ONLY_I2O1_ITEMS:
    I2O1_INSTRUCTIONS.add(f"{i}_i32")

variable_pattern = re.compile(r'^[A-Za-z_@][_@()\[\]\w]+')


def test_parameter_type(param: str) -> str:
    """Test a parameter if it's a "immediate_integer", "immediate_float", "variable" or "invalid" """
    if type(param) is not str or len(param) == 0:
        return "invalid"
    if variable_pattern.match(param):
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
    input_vars: List[str] = field(default_factory=list)
    output_vars: List[str] = field(default_factory=list)
    raw_instructions: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.update_types()

    def update_types(self):
        self.src1_type = test_parameter_type(self.src1)
        self.src2_type = test_parameter_type(self.src2)

    def dump(self) -> str:
        if self.instruction == "label":
            return F":{self.src1}"
        if self.instruction in NOARG_INSTRUCTIONS:
            return F"{self.instruction}"
        if self.instruction in O1_INSTRUCTIONS:
            return F"{self.instruction} {self.dest}"
        if self.instruction in I1_INSTRUCTIONS:
            return F"{self.instruction} {self.src1}"
        if self.instruction in I1O1_INSTRUCTIONS:
            return F"{self.instruction} {self.src1} {self.dest}"
        if self.instruction in I2O1_INSTRUCTIONS:
            return F"{self.instruction} {self.src1} {self.src2} {self.dest}"
        if self.instruction in ("if", "ifnot"):
            return F"{self.instruction} {self.src1} {self.relop} {self.src2} goto {self.dest}"
        # if self.instruction == "asm"
        opt_v = "v" if self.instruction == "asm_volatile" else ""
        asm_begin = " ".join([f"__asm{opt_v}begin", str(len(self.input_vars)), ] + self.input_vars)
        asm_end = " ".join([f"__asm{opt_v}end", str(len(self.output_vars)), ] + self.output_vars)
        result = [asm_begin, ]
        result.extend(self.raw_instructions)
        result.append(asm_end)
        return "\n".join(result)

