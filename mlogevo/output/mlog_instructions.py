#!/usr/bin/python3
"""\
IR instruction implementation for mlog architecture.
just use mlog_ir_registry
"""
from typing import List, Dict, Tuple

condition_ops = {
    "==": "equal",
    "!=": "notEqual",
    "<": "lessThan",
    "<=": "lessThanEq",
    ">": "greaterThan",
    ">=": "greaterThanEq",
}

inverted_ops = {
    "==": "!=",
    "!=": "==",
    "<=": ">",
    ">=": "<",
    "<": ">=",
    ">": "<=",
}

mlog_ir_registry: Dict = {}


def mlog_ir_impl(name: str, types: Tuple = ()):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        if len(types) == 0:
            mlog_ir_registry[name] = func
            return wrapper
        for t in types:
            mlog_ir_registry[f"{name}_{t}"] = func
        return wrapper
    return decorator


@mlog_ir_impl("set", ("i32", "f64", "obj"))
def mlog_set(src: str, dest: str) -> List[str]:
    inst = F"set {dest} {src}"
    return [inst, ]


@mlog_ir_impl("__funcbegin")
@mlog_ir_impl("label")
def mlog_label(label) -> List[str]:
    """ label name w/o leading or trailing colon . """
    pseudo_inst = F"{label}:"
    return [pseudo_inst, ]


@mlog_ir_impl("goto")
def mlog_jump_always(label: str) -> List[str]:
    inst = F"jump {label} always 0 0"
    return [inst, ]


@mlog_ir_impl("if")
def mlog_jump_if(arg1, rel_op, arg2, label) -> List[str]:
    condition_op = condition_ops[rel_op]
    inst = F"jump {label} {condition_op} {arg1} {arg2}"
    return [inst, ]


@mlog_ir_impl("ifnot")
def mlog_jump_ifnot(arg1, rel_op, arg2, label) -> List[str]:
    inv_op = inverted_ops[rel_op]
    condition_op = condition_ops[inv_op]
    inst = F"jump {label} {condition_op} {arg1} {arg2}"
    return [inst, ]


@mlog_ir_impl("add", ("i32", "f64"))
def mlog_add(src1, src2, dest) -> List[str]:
    inst = F"op add {dest} {src1} {src2}"
    return [inst, ]


@mlog_ir_impl("sub", ("i32", "f64"))
def mlog_sub(src1, src2, dest) -> List[str]:
    inst = F"op sub {dest} {src1} {src2}"
    return [inst, ]


@mlog_ir_impl("mul", ("i32", "f64"))
def mlog_mul(src1, src2, dest) -> List[str]:
    inst = F"op mul {dest} {src1} {src2}"
    return [inst, ]


@mlog_ir_impl("div", ("f64", ))
def mlog_div(src1, src2, dest) -> List[str]:
    inst = F"op div {dest} {src1} {src2}"
    return [inst, ]


@mlog_ir_impl("div", ("i32", ))
def mlog_idiv(src1, src2, dest) -> List[str]:
    inst = F"op idiv {dest} {src1} {src2}"
    return [inst, ]


@mlog_ir_impl("rem", ("i32", ))
def mlog_mod(src1, src2, dest) -> List[str]:
    inst = F"op mod {dest} {src1} {src2}"
    return [inst, ]


@mlog_ir_impl("floor", ("f64", ))
@mlog_ir_impl("cvtf64", ("i32", ))
def mlog_floor(src, dest) -> List[str]:
    inst = F"op floor {dest} {src} 0"
    return [inst, ]


@mlog_ir_impl("ceil", ("f64", ))
def mlog_ceil(src, dest) -> List[str]:
    inst = F"op ceil {dest} {src} 0"
    return [inst, ]


@mlog_ir_impl("minus", ("i32", "f64"))
def mlog_minus(src, dest) -> List[str]:
    inst = F"op sub {dest} 0 {src}"
    return [inst, ]


@mlog_ir_impl("and", ("i32", ))
def mlog_and(src1, src2, dest) -> List[str]:
    return [F"op and {dest} {src1} {src2}", ]


@mlog_ir_impl("or", ("i32", ))
def mlog_or(src1, src2, dest) -> List[str]:
    return [F"op or {dest} {src1} {src2}", ]


@mlog_ir_impl("xor", ("i32", ))
def mlog_xor(src1, src2, dest) -> List[str]:
    return [F"op xor {dest} {src1} {src2}", ]


@mlog_ir_impl("lsh", ("i32", ))
def mlog_shl(src1, src2, dest) -> List[str]:
    return [F"op shl {dest} {src1} {src2}", ]


@mlog_ir_impl("rsh", ("i32", ))
def mlog_shr(src1, src2, dest) -> List[str]:
    return [F"op shr {dest} {src1} {src2}", ]


@mlog_ir_impl("not", ("i32", ))
def mlog_flip(src1, dest) -> List[str]:
    return [F"op xor {dest} {src1} 0xFFFFFFFF", ]


@mlog_ir_impl("lt", ("i32", "f64"))
def mlog_less(src1, src2, dest) -> List[str]:
    return [F"op lessThan {dest} {src1} {src2}", ]


@mlog_ir_impl("gt", ("i32", "f64"))
def mlog_greater(src1, src2, dest) -> List[str]:
    return [F"op greaterThan {dest} {src1} {src2}", ]


@mlog_ir_impl("lteq", ("i32", "f64"))
def mlog_less_equal(src1, src2, dest) -> List[str]:
    return [F"op lessThanEq {dest} {src1} {src2}", ]


@mlog_ir_impl("gteq", ("i32", "f64"))
def mlog_greater_equal(src1, src2, dest) -> List[str]:
    return [F"op greaterThanEq {dest} {src1} {src2}", ]


@mlog_ir_impl("eq", ("i32", "f64"))
def mlog_equal(src1, src2, dest) -> List[str]:
    return [F"op equal {dest} {src1} {src2}", ]


@mlog_ir_impl("ne", ("i32", "f64"))
def mlog_not_equal(src1, src2, dest) -> List[str]:
    return [F"op notEqual {dest} {src1} {src2}", ]


@mlog_ir_impl("noop", ("i32", "f64"))
def mlog_noop() -> List[str]:
    return ["op xor __mlogev_nop __mlogev_nop 0", ]


@mlog_ir_impl("__call")
def mlog_call(function_name) -> List[str]:
    return [
        F"op add retaddr@{function_name} @counter 1",
        F"jump {function_name} always 1 1"
    ]


@mlog_ir_impl("__funcend")
@mlog_ir_impl("__return")
def mlog_return(function_name) -> List[str]:
    return [F"set @counter retaddr@{function_name}", ]
