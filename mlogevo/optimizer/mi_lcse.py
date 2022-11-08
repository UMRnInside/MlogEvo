from dataclasses import dataclass, field
from ..backend.basic_block import BasicBlock
from .optimizer_registry import register_optimizer


@dataclass
class Node:
    op: str
    inputs: list[int]
    outputs: list[str]


@register_optimizer(
    name="lcse",
    target="basic_block",
    is_machine_dependent=False,
    rank=10,
    optimize_level=1
)
def eliminate_local_common_subexpression(basic_block: BasicBlock, functions: dict):
    variable_version = {}
    regenerated = []
    for ir_inst in basic_block.instructions:
        pass

