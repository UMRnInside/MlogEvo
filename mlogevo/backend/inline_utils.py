from typing import Iterable, Tuple, List, Dict

from ..intermediate import Quadruple
from ..intermediate.function import Function


def should_inline(function: Function, arch="mlog") -> bool:
    if function.name == "main":
        return False
    if "inline" not in function.attributes:
        return False
    if "always_inline" in function.attributes:
        return True
    if arch == "mlog":
        return mlog_should_inline(function)
    return False


def mlog_should_inline(function: Function) -> bool:
    size = 0
    for inst in function.instructions:
        if inst.instruction in ("__funcbegin", "__funcend"):
            continue
        if inst.instruction == "__call":
            # TODO: consider inline functions that calls other functions
            return False
        if inst.instruction in ("label",):
            # size += 0
            continue
        if inst.instruction == "asm":
            size += len(inst.raw_instructions)
            continue
        size += 1
    # __call:2, __return:1, set return value: 1
    return size <= 16


def filter_inlineable_functions(functions: Iterable[Function], arch: str = "mlog") \
        -> Tuple[Dict[str, Function], Dict[str, Function]]:
    inline_functions: Dict[str, Function] = {}
    common_functions: Dict[str, Function] = {}
    for function in functions:
        if should_inline(function, arch):
            inline_functions[function.name] = function
        else:
            common_functions[function.name] = function
    return inline_functions, common_functions


def inline_calls(common_function_name: str,
                 common_function_body: List[Quadruple],
                 inline_functions: Dict[str, Function],) -> List[Quadruple]:
    result_irs: List[Quadruple] = []
    ctr = 0
    for ir in common_function_body:
        if ir.instruction != "__call":
            result_irs.append(ir)
            continue
        if ir.src1 not in inline_functions.keys():
            result_irs.append(ir)
            continue
        ctr += 1
        inlined_target = inline_functions[ir.src1]
        inlined_body = inlined_target.instructions
        assert len(inlined_body) >= 2
        return_jump = f"__MLOGEV_INLINE_CALL_{inlined_target.name}_{common_function_name}_{ctr}__"
        for inst in inlined_body:
            if inst.instruction in ("__funcbegin", "__funcend"):
                continue
            if inst.instruction == "__return":
                result_irs.append(Quadruple("goto", return_jump))
                continue
            result_irs.append(inst)
        result_irs.append(Quadruple("label", return_jump))
    return result_irs
