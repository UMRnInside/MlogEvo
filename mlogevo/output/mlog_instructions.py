#!/usr/bin/python3

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

def mlog_set(src: str, dest: str) -> list[str]:
    inst = F"set {dest} {src}"
    return [inst, ]

def mlog_label(label) -> list[str]:
    """ label name w/o leading or trailing colon . """
    real_label_name = label
    pseudo_inst = F"{real_label_name}:"
    return [pseudo_inst, ]

def mlog_jump_always(label: str) -> list[str]:
    inst = F"jump {label} always 0 0"
    return [inst, ]

def mlog_jump_if(arg1, rel_op, arg2, label) -> list[str]:
    condition_op = condition_ops[rel_op]
    inst = F"jump {label} {condition_op} {arg1} {arg2}"
    return [inst, ]

def mlog_jump_ifnot(arg1, rel_op, arg2, label) -> list[str]:
    inv_op = inverted_ops[rel_op]
    condition_op = condition_ops[inv_op]
    inst = F"jump {label} {condition_op} {arg1} {arg2}"
    return [inst, ]

def mlog_setpc(pc_value) -> list[str]:
    inst = F"set @counter {pc_value}"
    return [inst, ]

def mlog_rjump(offset) -> list[str]:
    inst = F"op add @counter @counter {offset}"
    return [inst, ]

def mlog_add(src1, src2, dest) -> list[str]:
    inst = F"op add {dest} {src1} {src2}"
    return [inst, ]

def mlog_sub(src1, src2, dest) -> list[str]:
    inst = F"op sub {dest} {src1} {src2}"
    return [inst, ]

def mlog_mul(src1, src2, dest) -> list[str]:
    inst = F"op sub {dest} {src1} {src2}"
    return [inst, ]

def mlog_div(src1, src2, dest) -> list[str]:
    inst = F"op div {dest} {src1} {src2}"
    return [inst, ]

def mlog_idiv(src1, src2, dest) -> list[str]:
    inst = F"op idiv {dest} {src1} {src2}"
    return [inst, ]

def mlog_mod(src1, src2, dest) -> list[str]:
    Ginst = F"op mod {dest} {src1} {src2}"
    return [inst, ]

def mlog_floor(src, dest) -> list[str]:
    inst = F"op floor {dest} {src} 0"
    return [inst, ]

def mlog_ceil(src, dest) -> list[str]:
    inst = F"op ceil {dest} {src} 0"
    return [inst, ]

def mlog_minus(src, dest) -> list[str]:
    inst = F"op sub {dest} 0 {src}"
    return [inst, ]

# TODO: strict 32-bit logical operands
def mlog_and(src1, src2, dest, strict_32bit) -> list[str]:
    insts = []
    insts.append( F"op b-and {dest} {src1} {src2}" )
    return insts

def mlog_or(src1, src2, dest, strict_32bit) -> list[str]:
    insts = []
    insts.append( F"op or {dest} {src1} {src2}" )
    return insts

def mlog_xor(src1, src2, dest, strict_32bit) -> list[str]:
    insts = []
    insts.append( F"op xor {dest} {src1} {src2}" )
    if strict_32bit:
        insts.append( F"op b-and {dest} {dest} 0xFFFFFFFF")
    return insts

def mlog_shl(src1, src2, dest, strict_32bit) -> list[str]:
    insts = []
    insts.append( F"op shl {dest} {src1} {src2}" )
    if strict_32bit:
        insts.append( F"op b-and {dest} {dest} 0xFFFFFFFF")
    return insts

def mlog_shr(src1, src2, dest, strict_32bit) -> list[str]:
    insts = []
    insts.append( F"op shr {dest} {src1} {src2}" )
    if strict_32bit:
        insts.append( F"op b-and {dest} {dest} 0xFFFFFFFF" )
    return insts

def mlog_flip(src1, dest, strict_32bit) -> list[str]:
    insts = []
    if strict_32bit:
        insts.append( F"op b-and {dest} {src1} 0xFFFFFFFF" )
        insts.append( F"op xor {dest} {src1} 0xFFFFFFFF" )
    else:
        insts.append( F"op xor {dest} {src1} 0xFFFFFFFF" )
    return insts

def mlog_noop() -> list[str]:
    return ["op xor __mlogev_nop __mlogev_nop 0", ]

def mlog_call(function_name) -> list[str]:
    insts = []
    insts.append( F"op add _retaddr_{function_name} @counter 1" )
    insts.append( F"jump {function_name} always 1 1" )
    return insts

def mlog_return(function_name) -> list[str]:
    inst = F"set @counter _retaddr_{function_name}"
    return [inst, ]