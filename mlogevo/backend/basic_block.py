from dataclasses import dataclass, field

from ..intermediate import Quadruple

# -1: no such block
# -2: not filled in yet
@dataclass
class BasicBlock:
    id: int
    instructions: list[Quadruple] = field(default_factory=list)
    jump_destination: int = -1

BASIC_BLOCK_ENTRANCES = set([
    "__funcbegin",
    "label",
])

BASIC_BLOCK_EXITS = set([
    "__funcend",
    "__return",
    "if",
    "ifnot",
    "goto",
])

def extract_destination_label(ir: Quadruple) -> str:
    if ir.instruction == "goto":
        return ir.src1
    if ir.instruction in ("if", "ifnot"):
        return ir.dest
    return ""

def get_basic_blocks(ir_list: list[Quadruple]) -> dict[int, BasicBlock]:
    basic_blocks: dict[int, BasicBlock] = {}
    current_block = []
    allocated = 0
    def submit_current_block():
        # -2: not filled in yet
        block = BasicBlock(allocated, current_block, -2)
        basic_blocks[allocated] = block
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

    label_owner: dict[str, int] = {}
    for (block_id, block) in basic_blocks.items():
        for ir in block.instructions:
            if ir.instruction != "label":
                break
            label_owner[ir.src1] = block_id

    for (block_id, block) in basic_blocks.items():
        if len(block.instructions) == 0:
            continue
        if block.instructions[-1] not in BASIC_BLOCK_EXITS:
            continue
        dest = extract_destination_label(block.instructions[-1])
        block.jump_destination = label_owner.get(dest, -1)

    return basic_blocks
