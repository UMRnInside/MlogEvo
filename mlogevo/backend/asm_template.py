import re
from typing import List
from ..intermediate import Quadruple

template_pattern = re.compile(r"%([\w\d]+|%|=)")


def mlog_replace_template(match: re.Match, variables: list, unique_number: int) -> str:
    # TODO: %[...] aliases
    src = match.group(1)
    if src == "=":
        return str(unique_number)
    if src == "%":
        return "%"
    return variables[int(src)]


def mlog_expand_asm_template(asm_inst: Quadruple, unique_number: int) -> List[str]:
    results = []
    variables = asm_inst.output_vars + asm_inst.input_vars
    replacer = lambda s: mlog_replace_template(s, variables, unique_number)

    for asm_line in asm_inst.raw_instructions:
        res_line = re.sub(template_pattern, replacer, asm_line)
        results.append(res_line)
    return results
