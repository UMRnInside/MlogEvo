"""
The __init__ of mlogevo.optimizer.
Has 2 dictionary named machine_dependant_optimizers and machine_independant_optimizers
Each of them looks like { optimizername: (function, target_scope) }
optimizername: str, target_scope: str

This module also provides append_optimizers() function
"""
# Import mi_ and md_ first to register optimizers
# optimizer functions are decorated by @register_optimizer
from typing import List, Dict
from . import mi_deduplicate_tail_return
from . import mi_remove_unused_labels
from . import mi_reorder_decls
from . import mi_lcse

from .optimizer_registry import \
    machine_dependent_optimizers, \
    machine_independent_optimizers, \
    md_flags_per_level, mi_flags_per_level


def _make_optimizers(choices: List, optimizers: Dict, options: List):
    excluded = set()
    for option in options:
        if option.startswith("no-"):
            excluded.add(option[3:])
    for option in options:
        if option in optimizers.keys():
            if option in excluded:
                continue
            triplet = optimizers[option]
            # name: (function, target, rank)
            choices.append(triplet)
    return choices


def _get_flags_by_level(src, flags_per_level, level=0):
    result = []
    for i in range(0, level + 1):
        result.extend(flags_per_level[i])
    result.extend(src)
    return result


def append_optimizers(backend, machine_dependents, machine_independents, level=0):
    """Automatically append optimizers to Backend object """
    # TODO: what are they?
    md_optimizers = []
    mi_optimizers = []

    md_flags = _get_flags_by_level(machine_dependents, md_flags_per_level, level)
    mi_flags = _get_flags_by_level(machine_independents, mi_flags_per_level, level)
    # TODO: machine-dependent optimizers
    _make_optimizers(md_optimizers, machine_dependent_optimizers, md_flags)
    _make_optimizers(mi_optimizers, machine_independent_optimizers, mi_flags)

    # md_optimizers.sort(key=lambda triplet: triplet[2])
    mi_optimizers.sort(key=lambda triplet: triplet[2])
    backend.mi_optimizers = mi_optimizers
