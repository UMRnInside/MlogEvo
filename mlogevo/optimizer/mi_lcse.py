import logging
import copy
from dataclasses import dataclass, field
from typing import NamedTuple, Dict, Tuple, List, Set
from collections import defaultdict, deque
from ..intermediate import Quadruple
from ..intermediate.ir_quadruple import I1_INSTRUCTIONS, I1O1_INSTRUCTIONS, I2O1_INSTRUCTIONS, O1_INSTRUCTIONS
from ..backend.basic_block import BasicBlock, BASIC_BLOCK_ENTRANCES, BASIC_BLOCK_EXITS
from .optimizer_registry import register_optimizer
logging.basicConfig(level=logging.DEBUG)
lcse_logger = logging.getLogger("lcse")


# immediate integers/floats has version 0, this is expected
class VersionedVariable(NamedTuple):
    name: str
    version: int = 0

    def __str__(self):
        return f"({self.name}: {self.version})"


class VersionedVariableDict(dict):
    def __missing__(self, key):
        default = VersionedVariable(key, 0)
        self[key] = default
        return default


class CacheableOp(NamedTuple):
    instruction: str
    src1: VersionedVariable
    src2: VersionedVariable
    # Do we need this?
    # dest: VersionedVariable


@dataclass
class DagNode:
    id: int
    instruction: str
    # List[(Node, nth output)]
    depends: List[Tuple] = field(default_factory=list)
    rdepends: List = field(default_factory=list)
    provides: List[VersionedVariable] = field(default_factory=list)
    # Optional, for asm block only
    original_ir: Quadruple = None

    def prettify(self, prefix="", indent="  ") -> str:
        result = [
            f"{prefix}Node #{self.id}, {self.instruction}:",
            f"{prefix}{indent}Depends:",
        ]
        for node, pos in self.depends:
            result.append(f"{prefix}{indent*2}Node {node.id}, output {pos}")
        result.append(f"{prefix}{indent}Provides:")
        for var in self.provides:
            result.append(f"{prefix}{indent * 2}{var}")
        return "\n".join(result)


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
        functions: Dict,
        known_variable_types: Dict[str, str]
) -> BasicBlock:
    lcse_logger.debug("*** START LCSE ***")

    variable_provider: Dict[VersionedVariable, Tuple[DagNode, int]] = {}
    variable_version: Dict[str, VersionedVariable] = VersionedVariableDict()
    aliases: Dict[VersionedVariable, VersionedVariable] = {}
    # Intended for those instructions that has only 1 output
    op_to_node: Dict[CacheableOp, DagNode] = {}
    dag_nodes: List[DagNode] = []

    ending: Quadruple = None
    result: List[Quadruple] = []

    tmpi = basic_block.instructions[-1].instruction
    callee = ""
    if tmpi in BASIC_BLOCK_EXITS:
        ending = basic_block.instructions[-1]
    if ending and ending.instruction == "__call":
        callee = ending.src1

    # explicitly building DAG, track variable versions
    for ir in basic_block.instructions:
        if ir is ending:
            continue
        if ir.instruction in BASIC_BLOCK_ENTRANCES or ir.instruction.startswith("decl_"):
            result.append(ir)
            continue
        if ir.instruction == "asm":
            i = len(dag_nodes)
            new_ir = copy.copy(ir)
            new_ir.input_vars = []
            node = DagNode(i, "asm", [], [], [], new_ir)
            dag_nodes.append(node)
            for input_var_name in ir.input_vars:
                true_var = get_variable_true_name(variable_version[input_var_name], aliases)
                depends_on = find_node_for_variable(true_var, variable_provider, dag_nodes, aliases)
                # Pending rewriting
                # new_ir.input_vars.append(true_var.name)
                node.depends.append(depends_on)
            for position, output_var_name in enumerate(ir.output_vars):
                old_output = variable_version[output_var_name]
                new_output = VersionedVariable(output_var_name, old_output.version + 1)
                variable_version[output_var_name] = new_output
                node.provides.append(new_output)
                variable_provider[new_output] = (node, position)
            continue
        old_dest = variable_version[ir.dest]
        new_dest = VersionedVariable(ir.dest, old_dest.version + 1)
        # update variable_version[dest] AFTER getting versions
        if ir.instruction.startswith("set_"):
            node, output_index = find_node_for_variable(
                variable_version[ir.src1], variable_provider, dag_nodes, aliases)
            variable_provider[new_dest] = (node, output_index)
            variable_version[ir.dest] = new_dest
            continue

        src1 = get_variable_true_name(variable_version[ir.src1], aliases)
        src2 = get_variable_true_name(variable_version[ir.src2], aliases)
        cacheable_op = CacheableOp(ir.instruction, src1, src2)
        node = op_to_node.get(cacheable_op)
        lcse_logger.debug(f"Op {cacheable_op.instruction} {cacheable_op.src1} {cacheable_op.src2}"
                          f"-> Node {node and node.id}")
        if node is None:
            src1_dep = find_node_for_variable(src1, variable_provider, dag_nodes, aliases)
            src2_dep = find_node_for_variable(src2, variable_provider, dag_nodes, aliases)
            i = len(dag_nodes)
            node = DagNode(i, ir.instruction, [src1_dep, src2_dep], [], [new_dest, ])
            dag_nodes.append(node)
            variable_provider[new_dest] = (node, 0)
            op_to_node[cacheable_op] = node
        else:
            aliases[new_dest] = node.provides[0]
        variable_version[ir.dest] = new_dest

    # This modifies aliases[]
    reverse_aliases = get_reverse_aliases(variable_version, aliases, callee, True)
    for node in dag_nodes:
        p = []
        for output in node.provides:
            p.append(get_variable_true_name(output, aliases))
        node.provides = p

    alive_node_ids = detect_alive_nodes(dag_nodes, variable_version, variable_provider, aliases)
    in_degrees = initialize_topo_from_node_list(dag_nodes, alive_node_ids)
    q = deque()
    # BEGIN topological sort
    for (node_id, degree) in in_degrees.items():
        if degree == 0 and node_id in alive_node_ids:
            q.append(node_id)
    while len(q) > 0:
        current_node = dag_nodes[q.popleft()]
        for rdep in current_node.rdepends:
            assert isinstance(rdep, DagNode)
            in_degrees[rdep.id] -= 1
            if in_degrees[rdep.id] == 0:
                q.append(rdep.id)

    # END topological sort

    # basic_block.instructions = result + endings
    # for node in dag_nodes:
    #     print(node.prettify(), "\n")
    # print("\n".join([r.dump() for r in result]))
    # print(ending)
    return basic_block


def find_node_for_variable(
        variable: VersionedVariable,
        variable_provider: Dict[VersionedVariable, Tuple[DagNode, int]],
        dag_nodes: List[DagNode],
        aliases: Dict[VersionedVariable, VersionedVariable]
) -> Tuple[DagNode, int]:
    variable = get_variable_true_name(variable, aliases)
    provider = variable_provider.get(variable)
    # Constants, global variables, or something from other basic blocks
    if provider is None:
        i = len(dag_nodes)
        # "": exists before this basic block
        node = DagNode(i, "", provides=[variable, ])
        dag_nodes.append(node)
        variable_provider[variable] = (node, 0)
        return node, 0
    steps = 0
    while provider[0].instruction.startswith("set_") and len(provider[0].depends) > 0:
        provider = provider.depends[0]
        steps += 1
        if steps > 1000000:
            raise ValueError(f"Too many steps on DAG (while finding {variable})! Is there any cycles?")
    return provider


def get_variable_true_name(
        variable: VersionedVariable,
        aliases: Dict[VersionedVariable, VersionedVariable]
) -> VersionedVariable:
    if variable not in aliases:
        return variable
    aliases[variable] = get_variable_true_name(aliases[variable], aliases)
    return aliases[variable]


def initialize_topo_from_node_list(dag_nodes: List[DagNode], alive_node_ids: Set[int]) -> Dict[int, int]:
    degree_in: Dict[int, int] = {}
    for node in dag_nodes:
        degree_in[node.id] = 0
        for dep, _ in node.depends:
            assert isinstance(dep, DagNode)
            if dep.id not in alive_node_ids:
                continue
            degree_in[node.id] += 1
            dep.rdepends.append(node)
    return degree_in


def detect_alive_nodes(
        dag_nodes: List[DagNode],
        variable_version: Dict[str, VersionedVariable],
        variable_provider: Dict[VersionedVariable, Tuple[DagNode, int]],
        aliases: Dict[VersionedVariable, VersionedVariable],
) -> Set[int]:
    alive_node_ids: Set[int] = set()
    # Store node IDs. ID -> index in dag_nodes
    q = deque()
    for (_, alive_var) in variable_version.items():
        node, _ = find_node_for_variable(alive_var, variable_provider, dag_nodes, aliases)
        if node.id in alive_node_ids:
            continue
        alive_node_ids.add(node.id)
        q.append(node.id)

    while len(q) > 0:
        current_node = dag_nodes[q.popleft()]
        for (node, _) in current_node.depends:
            if node.id in alive_node_ids:
                continue
            alive_node_ids.add(node.id)
            q.append(node.id)
    return alive_node_ids


def get_reverse_aliases(
        variable_version: Dict[str, VersionedVariable],
        aliases: Dict[VersionedVariable, VersionedVariable],
        callee: str,
        adjustment_desired = False
) -> Dict[VersionedVariable, Set[VersionedVariable]]:
    # TODO: rewrite DagNode.provides
    def evaluate_weight(var: VersionedVariable) -> int:
        weight = 0
        if not var.name.startswith("__vtmp_") and not var.name.startswith("___vtmp_"):
            weight += 1
        if variable_version[var.name] == var:
            weight += 2
        if "@" not in var.name:
            # global variables
            weight += 4
        if "@" in var.name and var.name.split("@")[-1] == callee:
            weight += 8
        return weight

    alias_group: Dict[VersionedVariable, Set[VersionedVariable]] = defaultdict(set)
    for (derived, base) in aliases.items():
        alias_group[base].add(get_variable_true_name(derived, aliases))
    if not adjustment_desired:
        return alias_group

    for (old_base, candidates) in alias_group.items():
        best_base = max(old_base, *candidates, key=evaluate_weight)
        if best_base == old_base:
            continue
        aliases[old_base] = best_base
        for candidate in candidates:
            aliases[candidate] = best_base
        if best_base in aliases.keys():
            del aliases[best_base]

    alias_group = defaultdict(set)
    for (derived, base) in aliases.items():
        alias_group[base].add(get_variable_true_name(derived, aliases))
    return alias_group
