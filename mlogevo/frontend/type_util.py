from pycparser.c_ast import TypeDecl

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

def get_binaryop_result_type(type_l, type_r):
    rank_l = CONVERSION_RANK[type_l]
    rank_r = CONVERSION_RANK[type_r]
    if rank_l < rank_r:
        return type_r
    return type_l

def get_instruction_name(operator) -> str:
    return ""
