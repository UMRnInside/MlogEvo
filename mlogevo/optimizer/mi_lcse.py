import logging
import copy
from dataclasses import dataclass, field
from typing import NamedTuple, Dict, Tuple, List, Set
from collections import defaultdict, deque
from ..intermediate import Quadruple
from ..intermediate.ir_quadruple import I1_INSTRUCTIONS, I1O1_INSTRUCTIONS, I2O1_INSTRUCTIONS, O1_INSTRUCTIONS
from ..backend.basic_block import BasicBlock, BASIC_BLOCK_ENTRANCES, BASIC_BLOCK_EXITS
from .optimizer_registry import register_optimizer
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
        rl = [x.id for x in self.rdepends]
        result.append(f"{prefix}{indent}Used by: {rl}")
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
    lcse_logger.debug("basic block content:")
    lcse_logger.debug("\n".join([v.dump() for v in basic_block.instructions]))

    variable_provider: Dict[VersionedVariable, Tuple[DagNode, int]] = {}
    variable_version: Dict[str, VersionedVariable] = VersionedVariableDict()
    aliases: Dict[VersionedVariable, VersionedVariable] = {}
    # Intended for those instructions that has only 1 output
    op_to_node: Dict[CacheableOp, DagNode] = {}
    dag_nodes: List[DagNode] = []

    ending: Quadruple = None
    ending_node: DagNode = None
    result: List[Quadruple] = []

    tmpi = basic_block.instructions[-1].instruction
    callee = ""
    if tmpi in BASIC_BLOCK_EXITS:
        ending = basic_block.instructions[-1]
    if ending and ending.instruction == "__call":
        callee = ending.src1

    # explicitly building DAG, track variable versions
    for ir in basic_block.instructions:
        if ir.instruction in BASIC_BLOCK_ENTRANCES or ir.instruction.startswith("decl_"):
            result.append(ir)
            continue
        ir.update_types()
        if ir.instruction in ("asm", "asm_volatile"):
            i = len(dag_nodes)
            new_ir = copy.copy(ir)
            new_ir.input_vars = []
            node = DagNode(i, ir.instruction, [], [], [], new_ir)
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
            if ir is ending:
                ending_node = node
            continue
        old_dest = variable_version[ir.dest]
        new_dest = VersionedVariable(ir.dest, old_dest.version + 1)
        # update variable_version[dest] AFTER getting versions
        if ir.instruction.startswith("set_"):
            lcse_logger.debug(f"Op {ir.instruction} {ir.src1} {ir.dest}")
            node, output_index = find_node_for_variable(
                variable_version[ir.src1], variable_provider, dag_nodes, aliases)
            if ir.src1_type == "variable":
                # TODO this causes bug
                lcse_logger.debug(f"provider of {new_dest} is Node {node.id} Output {output_index}")
                variable_provider[new_dest] = (node, output_index)
                aliases[new_dest] = node.provides[output_index]
            else:
                i = len(dag_nodes)
                node = DagNode(i, ir.instruction, [(node, output_index), ], [], [new_dest, ], ir)
                dag_nodes.append(node)
                variable_provider[new_dest] = (node, 0)
            variable_version[ir.dest] = new_dest
            continue

        src1 = get_variable_true_name(variable_version[ir.src1], aliases)
        src2 = get_variable_true_name(variable_version[ir.src2], aliases)
        cacheable_op = CacheableOp(ir.instruction, src1, src2)
        node = op_to_node.get(cacheable_op)
        lcse_logger.debug(f"Op {cacheable_op.instruction} {cacheable_op.src1} {cacheable_op.src2}"
                          f"-> Node {node and node.id}")
        if node is None:
            deps = []
            if ir.src1_type != "":
                src1_dep = find_node_for_variable(src1, variable_provider, dag_nodes, aliases)
                deps.append(src1_dep)
            if ir.src2_type != "":
                src2_dep = find_node_for_variable(src2, variable_provider, dag_nodes, aliases)
                deps.append(src2_dep)
            i = len(dag_nodes)
            node = DagNode(i, ir.instruction, deps, [], [new_dest, ], ir)
            dag_nodes.append(node)
            variable_provider[new_dest] = (node, 0)
            op_to_node[cacheable_op] = node
        else:
            aliases[new_dest] = node.provides[0]
        # Uncomment these if we do `lazy fulfill` on variable aliases
        # old_provider = find_node_for_variable(old_dest, variable_provider, dag_nodes, aliases)[0]
        # old_provider.rdepends.append(node)
        variable_version[ir.dest] = new_dest
        if ir is ending:
            ending_node = node

    # make sure ending node appears AFTER all other nodes
    # in topological order
    if ending_node is not None:
        for node in dag_nodes:
            if node is ending_node:
                continue
            node.rdepends.append(ending_node)
    # This modifies aliases[]
    # TODO: should we adjust aliases?
    reverse_aliases = get_reverse_aliases(variable_version, aliases, callee, False)
    for node in dag_nodes:
        p = []
        for output in node.provides:
            p.append(get_variable_true_name(output, aliases))
        node.provides = p

    active_node_ids = detect_active_nodes(dag_nodes, variable_version, variable_provider, aliases, ending_node)
    in_degrees = initialize_topo_from_node_list(dag_nodes, active_node_ids)
    q = deque()
    lcse_logger.debug(f"active variables: { {k: v.version for (k, v) in variable_version.items()} }")
    lcse_logger.debug(f"active nodes: {active_node_ids}")
    lcse_logger.debug(f"ending node: {ending_node}")
    # BEGIN topological sort
    for node in dag_nodes:
        lcse_logger.debug("\n"+node.prettify())
    for (node_id, degree) in in_degrees.items():
        if degree == 0 and node_id in active_node_ids:
            q.append(node_id)
    lcse_logger.debug(f"initial Toposort queue: {q}")
    lcse_logger.debug(f"in_degrees: {in_degrees}")
    while len(q) > 0:
        current_node = dag_nodes[q.popleft()]
        lcse_logger.debug(f"toposort on node {current_node.id}")
        tmpl = regenerate_instructions_from_node(current_node, variable_version, reverse_aliases, known_variable_types)
        lcse_logger.debug(f"this regenerates:")
        lcse_logger.debug("\n".join([v.dump() for v in tmpl]))
        result.extend(tmpl)
        for rdep in current_node.rdepends:
            assert isinstance(rdep, DagNode)
            in_degrees[rdep.id] -= 1
            if in_degrees[rdep.id] == 0:
                q.append(rdep.id)

    # END topological sort
    # Now we handle ending


    # for node in dag_nodes:
    #     print(node.prettify(), "\n")
    # print("\n".join([r.dump() for r in result]))
    # print(ending)
    # lcse_logger.debug(result)
    basic_block.instructions = result
    return basic_block


def find_node_for_variable(
        variable: VersionedVariable,
        variable_provider: Dict[VersionedVariable, Tuple[DagNode, int]],
        dag_nodes: List[DagNode],
        aliases: Dict[VersionedVariable, VersionedVariable],
        track_set_instructions=False
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
    if not track_set_instructions:
        return provider

    steps = 0
    last = provider
    set_instruction = provider[0].instruction
    while provider[0].instruction == set_instruction and len(provider[0].depends) > 0:
        last = provider
        provider = provider[0].depends[0]
        steps += 1
        if steps > 1000000:
            raise ValueError(f"Too many steps on DAG (while finding {variable})! Is there any cycles?")
    # do not track to constant nodes
    if provider[0].instruction == "":
        return last
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
        if node.id not in alive_node_ids:
            continue
        for dep, _ in node.depends:
            assert isinstance(dep, DagNode)
            if dep.id not in alive_node_ids:
                continue
            dep.rdepends.append(node)
    for node in dag_nodes:
        if node.id not in alive_node_ids:
            continue
        for rdep in node.rdepends:
            if rdep.id not in alive_node_ids:
                continue
            degree_in[rdep.id] += 1
    return degree_in


def detect_active_nodes(
        dag_nodes: List[DagNode],
        variable_version: Dict[str, VersionedVariable],
        variable_provider: Dict[VersionedVariable, Tuple[DagNode, int]],
        aliases: Dict[VersionedVariable, VersionedVariable],
        required_node: DagNode
) -> Set[int]:
    active_node_ids: Set[int] = set()
    # Store node IDs. ID -> index in dag_nodes
    q = deque()
    if required_node is not None:
        q.append(required_node.id)
        active_node_ids.add(required_node.id)
    for (_, active_var) in variable_version.items():
        node, _ = find_node_for_variable(active_var, variable_provider, dag_nodes, aliases)
        lcse_logger.debug(f"active variable {active_var} resolved to {get_variable_true_name(active_var, aliases)}")
        lcse_logger.debug(f"active variable {active_var} is from node {node.id}")
        if node.id in active_node_ids:
            continue
        active_node_ids.add(node.id)
        q.append(node.id)

    while len(q) > 0:
        current_node = dag_nodes[q.popleft()]
        for (node, _) in current_node.depends:
            if node.id in active_node_ids:
                continue
            active_node_ids.add(node.id)
            q.append(node.id)
    return active_node_ids


def get_reverse_aliases(
        variable_version: Dict[str, VersionedVariable],
        aliases: Dict[VersionedVariable, VersionedVariable],
        callee: str,
        adjustment_desired = False
) -> Dict[VersionedVariable, Set[VersionedVariable]]:

    def evaluate_weight(var: VersionedVariable) -> int:
        weight = 0
        if var.name.startswith("__vtmp_") or var.name.startswith("___vtmp_"):
            # Should we prefer temp variables?
            weight -= 1
        if variable_version[var.name] == var:
            weight += 8
        else:
            weight -= 8

        if "@" not in var.name:
            # global variables
            weight += 4
        if "@" in var.name and var.name.split("@")[-1] == callee:
            # NOTE: this depends on `__call` being basic block exits
            weight += 2
        return weight

    alias_group: Dict[VersionedVariable, Set[VersionedVariable]] = defaultdict(set)
    for (derived, base) in aliases.items():
        alias_group[get_variable_true_name(base, aliases)].add(derived)
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
        alias_group[get_variable_true_name(base, aliases)].add(derived)
    return alias_group


def write_active_aliases(
        base: VersionedVariable,
        var_type: str,
        alias_group: Dict[VersionedVariable, Set[VersionedVariable]],
        final_variable_version: Dict[str, VersionedVariable],
) -> List[Quadruple]:
    if len(base.name) == 0 or var_type is None:
        return []
    result = []
    for derived in alias_group[base]:
        if derived.name.startswith("___vtmp_"):
            # TODO: cross-block variable references?
            continue
        if final_variable_version[derived.name] == derived:
            lcse_logger.debug(f"write_active_aliases: {base} -> {derived}")
            result.append(Quadruple(f"set_{var_type}", src1=base.name, dest=derived.name))
    return result


def regenerate_instructions_from_node(
        node: DagNode,
        variable_version: Dict[str, VersionedVariable],
        alias_group: Dict[VersionedVariable, Set[VersionedVariable]],
        known_variable_types: Dict[str, str]
) -> List[Quadruple]:
    # Empty / constant nodes
    if node.instruction == "":
        return []
    result: List[Quadruple] = []
    alias_fillers: List[Quadruple] = []

    input_vars = []
    # Shared between ASM blocks and normal instructions
    for src_node, src_index in node.depends:
        input_vars.append(src_node.provides[src_index].name)

    if node.instruction in ("asm", "asm_volatile"):
        ir = node.original_ir
        for versioned_var in node.provides:
            old_var = VersionedVariable(versioned_var.name, versioned_var.version - 1)
            if old_var.version <= 0:
                tmpl = write_active_aliases(
                    old_var, known_variable_types.get(old_var.name), alias_group, variable_version
                )
                result.extend(tmpl)
            if versioned_var.version >= 1:
                tmpl = write_active_aliases(
                    versioned_var, known_variable_types.get(versioned_var.name), alias_group, variable_version
                )
                alias_fillers.extend(tmpl)
        ir.input_vars = input_vars
        result.append(ir)
        return result + alias_fillers
    if node.instruction in ("if", "ifnot"):
        ir = copy.copy(node.original_ir)
        src1, src2 = input_vars[0:2]
        result.append(ir)
        return result

    # Now we only have 1 output
    current_dest = node.provides[0]
    old_dest = VersionedVariable(current_dest.name, current_dest.version - 1)
    if old_dest.version <= 0:
        tmpl = write_active_aliases(old_dest, known_variable_types.get(old_dest.name), alias_group, variable_version)
        result.extend(tmpl)
    if current_dest.version >= 1:
        tmpl = write_active_aliases(
            current_dest, known_variable_types.get(current_dest.name), alias_group, variable_version
        )
        alias_fillers.extend(tmpl)

    if node.instruction in I1O1_INSTRUCTIONS:
        src1 = input_vars[0]
        ir = Quadruple(node.instruction, src1, "", current_dest.name)
        result.append(ir)
    elif node.instruction in I2O1_INSTRUCTIONS:
        src1, src2 = input_vars[0:2]
        ir = Quadruple(node.instruction, src1, src2, current_dest.name)
        result.append(ir)
    elif node.instruction in BASIC_BLOCK_EXITS:
        # BASIC_BLOCK_EXITS does not write to variables
        # they set `@counter` instead
        return [node.original_ir, ]
    else:
        raise ValueError(f"Unhandled DAG instruction: {node.instruction}")
    return result + alias_fillers
