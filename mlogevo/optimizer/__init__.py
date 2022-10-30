"""
The __init__ of mlogevo.optimizer.
Has 2 dictionary named machine_dependant_optimizers and machine_independant_optimizers
Each of them looks like { optimizername: (function, target_scope) }
optimizername: str, target_scope: str

This module also provides append_optimizers() function
"""
# Import mi_ and md_ first to register optimizers
# optimizer functions are decorated by @register_optimizer
from . import mi_deduplicate_tail_return
from . import mi_remove_unused_labels

from .optimizer_registry import \
        machine_dependant_optimizers, \
        machine_independant_optimizers


def _take_key_1(t):
    return t[1]

def _make_optimizers(optimizers, options):
    excluded = set()
    for option in options:
        if option.startswith("no-"):
            excluded.add(option[2:])
    for option in options:
        if option in machine_independant_optimizers.keys():
            if option in excluded:
                continue
            triplet = machine_independant_optimizers[option]
            # name: (function, target, rank)
            optimizers[triplet[1]].append( (triplet[0], triplet[2]) )
    return optimizers


def append_optimizers(backend, machine_dependants, machine_independants, level=0):
    """Automatically append optimizers to Backend object """
    # TODO: what are they?
    md_optimizers = {
    }

    mi_optimizers = {
        "function": [],
        "basic_block": [],
        "basic_block_graph": [],
    }

    # TODO: machine-dependant optimizers
    _make_optimizers(md_optimizers, machine_dependants)
    _make_optimizers(mi_optimizers, machine_independants)

    for li in mi_optimizers.values():
        li.sort(key=_take_key_1)

    backend.function_optimizers = [ t[0] for t in mi_optimizers["function"] ]
    backend.basic_block_optimizers = [ t[0] for t in mi_optimizers["basic_block"] ]
    backend.block_graph_optimizers = [ t[0] for t in mi_optimizers["basic_block_graph"] ]
