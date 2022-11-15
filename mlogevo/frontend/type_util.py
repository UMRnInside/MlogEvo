from pycparser.c_ast import TypeDecl, IdentifierType, Struct

# NOTE: only int and double invoked
CONVERSION_RANK = {
    "bool": 1,
    "char": 2,
    "short": 3,
    "int": 4,
    "long": 5,
    "long long": 6,
    "float": 7,
    "double": 8,
}

# TODO: new IR format
CORE_BINARY_OPERATORS = {
    "+": "add",
    "-": "sub",
    "*": "mul",
    "/": "div",
    "%": "rem",
    "&": "and",
    "|": "or",
    "^": "xor",
    "<<": "lsh",
    ">>": "rsh",
}

CORE_COMPARISONS = {
    "<": "lt",
    ">": "gt",
    "<=": "lteq",
    ">=": "gteq",
    "==": "eq",
    "!=": "ne",
}

CORE_UNARY_OPERATORS = {
    "~": "not",
    "-": "minus",
}

__type_int = IdentifierType(["int", ])
DUMMY_INT_TYPEDECL = TypeDecl("", [], [], __type_int)


def extract_typename(typedecl) -> str:
    if isinstance(typedecl, Struct):
        return f"struct {typedecl}"
    if isinstance(typedecl, str):
        return typedecl
    if isinstance(typedecl.type, IdentifierType):
        return typedecl.type.names[0]
    raise ValueError(f"Unknown TypeDecl: {typedecl}")


def get_arithmetic_result_type(type_l, type_r):
    rank_l = CONVERSION_RANK.get(extract_typename(type_l), None)
    rank_r = CONVERSION_RANK.get(extract_typename(type_r), None)
    if rank_l < rank_r:
        return type_r, rank_r
    return type_l, rank_l


def decorate_instruction(core, result_rank):
    return f"{core}_f64" if result_rank >= 7 else f"{core}_i32"


def choose_binaryop_instruction(operator, type_l, type_r):
    "type_l, type_r can be string 'int' or TypeDecl. return (typedecl, inst)"
    result_type, result_rank = get_arithmetic_result_type(type_l, type_r)

    if operator in CORE_COMPARISONS.keys():
        instruction = decorate_instruction(CORE_COMPARISONS[operator], result_rank)
        # TODO: type bool
        return DUMMY_INT_TYPEDECL, instruction
    if result_rank > 6 and operator in ("&", "|", "^", "<<", ">>"):
        raise ValueError(f"type {result_type} does NOT support logical operator {operator}")

    instruction = decorate_instruction(CORE_BINARY_OPERATORS[operator], result_rank)
    return result_type, instruction


def choose_unaryop_instruction(operator, typedecl):
    type_l = extract_typename(typedecl)
    result_rank = CONVERSION_RANK[type_l]
    if result_rank > 6 and operator == "~":
        raise ValueError(f"type {type_l} does NOT support operator {operator}")
    inst = decorate_instruction(CORE_UNARY_OPERATORS[operator], result_rank)
    return type_l, inst


def choose_set_instruction(typedecl):
    real_type = extract_typename(typedecl)
    if real_type in ("double", "float"):
        return "set_f64"
    if real_type == "struct MlogObject":
        return "set_obj"
    return "set_i32"
