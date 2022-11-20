import logging
from typing import NamedTuple, Dict, Tuple, List, Set
from ..intermediate import Quadruple
from ..backend.basic_block import BasicBlock, BASIC_BLOCK_ENTRANCES
from .optimizer_registry import register_optimizer
#logging.basicConfig(level=logging.DEBUG)
lcse_logger = logging.getLogger("lcse")


# immediate integers/floats has version 0, this is expected
class VersionedVariable(NamedTuple):
    name: str
    version: int


class CacheableOp(NamedTuple):
    instruction: str
    src1: VersionedVariable
    src2: VersionedVariable
    # Do we need this?
    # dest: VersionedVariable


@register_optimizer(
    name="lcse",
    target="basic_block",
    is_machine_dependent=False,
    rank=10,
    optimize_level=1
)
def eliminate_local_common_subexpression(
        basic_block: BasicBlock,
        current_function_name: str,
        functions: Dict
) -> BasicBlock:
    variable_version: Dict[str, VersionedVariable] = {}
    # Variable alias -> Variable
    aliases: Dict[VersionedVariable, VersionedVariable] = {}
    op_cache: Dict[CacheableOp, VersionedVariable] = {}
    referred: Set[VersionedVariable] = set()
    generation_1 = []
    callee = ""
    if basic_block.instructions[-1].instruction == "__call":
        callee = basic_block.instructions[-1].src1

    for ir_inst in basic_block.instructions:
        generation_1.extend(
            shorten(ir_inst, current_function_name, callee,
                    variable_version, aliases,
                    op_cache, referred)
        )
        if len(generation_1) == 0:
            continue
        last = generation_1[-1]
        # TODO: asm are block exits, but not every time asm jumps out of current block
        if last.instruction == "asm":
            continue
    # Reassign to clear variable_version
    active_variables = variable_version
    variable_version = {}
    generation_2 = []
    # If some aliases are active till the end, we should perform copy assignment on them
    for ir_inst in generation_1:
        if ir_inst.instruction in BASIC_BLOCK_ENTRANCES:
            generation_2.append(ir_inst)
            continue
        if ir_inst.dest == "":
            generation_2.append(ir_inst)
            continue
        # TODO: should we prefer writing to global variables?
        old_dest = get_last_version_of_variable(ir_inst.dest, variable_version)
        new_dest = VersionedVariable(ir_inst.dest, old_dest.version + 1)
        if old_dest == active_variables.get(ir_inst.dest):
            # TODO this can be faster
            for (cname, body) in aliases.items():
                if body != old_dest:
                    continue
                if cname == old_dest or cname not in active_variables.keys():
                    continue
                try:
                    operand_type = ir_inst.instruction.split("_")[-1]
                    copy_inst = f"set_{operand_type}"
                    generation_2.append(Quadruple(copy_inst, ir_inst.dest, "", cname))
                except IndexError:
                    raise ValueError(f"IR instruction {ir_inst.instruction} does NOT have a type, abort copying")
        generation_2.append(ir_inst)
        variable_version[ir_inst.dest] = new_dest

    basic_block.instructions = generation_2
    return basic_block


# We need callee,
def shorten(
        ir: Quadruple,
        current_function_name: str,
        callee: str,
        variable_version: Dict[str, VersionedVariable],
        aliases: Dict[VersionedVariable, VersionedVariable],
        op_cache: Dict[CacheableOp, VersionedVariable],
        referred: Set[VersionedVariable]
) -> List[Quadruple]:
    result_instructions: List[Quadruple] = []
    # BASIC_BLOCK_ENTRANCES don't create or modify variables
    if ir.instruction in BASIC_BLOCK_ENTRANCES:
        return [ir, ]
    if ir.instruction in ("goto", "__funcend"):
        return [ir, ]
    lcse_logger.debug(f"shorten(): handling ir: {ir.dump()}")
    if ir.instruction == "asm":
        new_input_vars = []
        for var in ir.input_vars:
            optimized_src = get_last_version_of_variable(var, variable_version)
            referred.add(optimized_src)
            new_input_vars.append(optimized_src.name)
        ir.input_vars = new_input_vars
        return [ir, ]

    if ir.src1 and ir.src1_type == "variable":
        referred.add(get_last_version_of_variable(ir.src1, variable_version))
    if ir.src2 and ir.src2_type == "variable":
        referred.add(get_last_version_of_variable(ir.src2, variable_version))

    if ir.instruction.startswith("set"):
        # Can we alias this or actually assign/copy it?
        # For global variables and function arguments: no
        if ir.src1_type != "variable" or should_keep_this_assignment(ir.dest, callee):
            return [ir, ]
        # It's safe to eliminate this set_(some type)
        old_dest = variable_version.get(ir.dest, VersionedVariable(ir.dest, 0))
        new_dest = VersionedVariable(ir.dest, old_dest.version + 1)
        src = get_last_version_of_variable(ir.src1, variable_version)
        lcse_logger.debug(f"alias {new_dest} = {src} created")
        variable_version[ir.dest] = new_dest
        aliases[new_dest] = src
        # add_alias(src, new_dest, aliases, variable_known_aliases)
        return result_instructions

    src1 = get_last_version_of_variable(ir.src1, variable_version)
    src2 = get_last_version_of_variable(ir.src2, variable_version)
    lcse_logger.debug(f"alias of {src1} is {aliases.get(src1)}")
    lcse_logger.debug(f"alias of {src2} is {aliases.get(src2)}")
    src1 = aliases.get(src1, src1)
    src2 = aliases.get(src2, src2)
    old_dest = variable_version.get(ir.dest, VersionedVariable(ir.dest, 0))
    current_op = CacheableOp(ir.instruction, src1, src2)
    lcse_logger.debug(f"old_dest = {old_dest}")
    lcse_logger.debug(f"current_op = {current_op}")
    if current_op in op_cache.keys():
        lcse_logger.debug(f"HIT op cache, creating alias {old_dest} = {op_cache[current_op]}")
        aliases[old_dest] = op_cache[current_op]
        # add_alias(op_cache[current_op], old_dest, aliases, variable_known_aliases)
    else:
        ir.src1 = src1.name
        ir.src2 = src2.name
        result_instructions.append(ir)
        new_dest = VersionedVariable(ir.dest, old_dest.version + 1)
        variable_version[ir.dest] = new_dest
        op_cache[current_op] = new_dest
    return result_instructions


# begin util functions
def get_last_version_of_variable(name: str, variable_version: Dict[str, VersionedVariable]) -> VersionedVariable:
    return variable_version.get(name, VersionedVariable(name, 0))


def should_keep_this_assignment(dest_name: str, callee: str):
    lcse_logger.debug(f"deciding {dest_name}")
    if "@" not in dest_name:
        lcse_logger.debug(f"keep assignment of {dest_name}: global variables")
        return True
    tokens = dest_name.split("@")
    if tokens[-1] == callee:
        lcse_logger.debug(f"keep assignment of {dest_name}: involved in function call")
        return True
    return False


def add_alias(
        base: VersionedVariable,
        alias: VersionedVariable,
        aliases: Dict[VersionedVariable, VersionedVariable],
        variable_known_aliases: Dict[VersionedVariable, List[VersionedVariable]]
) -> None:
    aliases[alias] = base
    if base in variable_known_aliases.keys():
        variable_known_aliases[base].append(alias)
    else:
        variable_known_aliases[base] = [alias, ]
# end util functions
