from dataclasses import dataclass, field
from typing import List, Dict
from ..intermediate import Quadruple


# -1: no such block
# -2: not filled in yet
@dataclass
class BasicBlock:
    id: int
    instructions: List[Quadruple] = field(default_factory=list)
    jump_destination: int = -1
    will_continue: bool = True


BASIC_BLOCK_ENTRANCES = {
    "__funcbegin",
    "label",
}

BASIC_BLOCK_EXITS = {
    "__funcend",
    "__call",
    "__return",
    "if",
    "ifnot",
    "goto",
    # asm may have multiple output, making things harder
    # TODO
    "asm",
}

NO_CONTINUES = {
    "goto", "__funcend",
}


def extract_destination_label(ir: Quadruple) -> str:
    if ir.instruction == "goto":
        return ir.src1
    if ir.instruction in ("if", "ifnot"):
        return ir.dest
    return ""


def get_basic_blocks(ir_list: List[Quadruple]) -> Dict[int, BasicBlock]:
    basic_blocks: Dict[int, BasicBlock] = {}
    current_block = []
    allocated = 0

    def submit_current_block():
        nonlocal allocated, current_block, basic_blocks
        # -2: not filled in yet
        basic_blocks[allocated] = BasicBlock(allocated, current_block, -1, True)
        current_block = []
        allocated += 1

    for ir in ir_list:
        if ir.instruction in BASIC_BLOCK_ENTRANCES:
            if len(current_block) == 0 \
                    or current_block[-1].instruction in BASIC_BLOCK_ENTRANCES:
                current_block.append(ir)
            else:
                submit_current_block()
                current_block.append(ir)
            continue
        if ir.instruction in BASIC_BLOCK_EXITS:
            current_block.append(ir)
            submit_current_block()
            continue
        current_block.append(ir)
    if len(current_block) > 0:
        submit_current_block()

    label_owner: Dict[str, int] = {}
    for (block_id, block) in basic_blocks.items():
        for ir in block.instructions:
            if ir.instruction != "label":
                break
            label_owner[ir.src1] = block_id

    for (block_id, block) in basic_blocks.items():
        if len(block.instructions) == 0:
            continue
        tail = block.instructions[-1]
        if tail.instruction in NO_CONTINUES:
            block.will_continue = False
        if tail.instruction not in BASIC_BLOCK_EXITS:
            continue
        dest = extract_destination_label(tail)
        block.jump_destination = label_owner.get(dest, -1)

    return basic_blocks
