from pycparser.c_ast import TypeDecl, IdentifierType

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
    if isinstance(typedecl, str):
        return typedecl
    return typedecl.type.names[0]


def get_arithmetic_result_type(type_l, type_r):
    rank_l = CONVERSION_RANK[extract_typename(type_l)]
    rank_r = CONVERSION_RANK[extract_typename(type_r)]
    if rank_l < rank_r:
        return (type_r, rank_r)
    return (type_l, rank_l)


def choose_binaryop_instruction(operator, type_l, type_r):
    "type_l, type_r can be string 'int' or TypeDecl. return (typedecl, inst)"
    result_type, result_rank = get_arithmetic_result_type(type_l, type_r)
    decorator = lambda inst: f"f{inst}" if result_rank >= 7 else f"{inst}l"

    if operator in CORE_COMPARISONS.keys():
        instruction = decorator(CORE_COMPARISONS[operator])
        # TODO: type bool
        return (DUMMY_INT_TYPEDECL, instruction)
    if result_rank > 6 and operator in ("&", "|", "^", "<<", ">>"):
        raise ValueError(f"type {result_type} does NOT support logical operator {operator}")

    instruction = decorator(CORE_BINARY_OPERATORS[operator])
    return (result_type, instruction)


def choose_unaryop_instruction(operator, type_l):
    result_rank = CONVERSION_RANK[type_l]
    if result_rank > 6 and operator == "~":
        raise ValueError(f"type {type_l} does NOT support operator {operator}")
    decorator = lambda inst: f"f{inst}" if result_rank >= 7 else f"{inst}l"
    inst = decorator(CORE_UNARY_OPERATORS[operator])
    return (type_l, inst)
