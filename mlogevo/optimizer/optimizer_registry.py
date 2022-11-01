# name: (function, target, rank)
machine_independent_optimizers = {}
machine_dependent_optimizers = {}

# [name1, name2, ... ]
md_flags_per_level = (
    # No flags on -O 0 (zero)
    [],
    [], [], [],
    # Level 4: not at ANY optimize level
    [],
)
mi_flags_per_level = (
    [],
    [], [], [],
    [],
)


# Collect optimizers, has side effects
def register_optimizer(name, target, is_machine_dependent, rank=999, optimize_level=4):
    """name: in command line, -fremove-unused-labels <-> remove-unused-labels
target: function, basic_block, basic_block_graph
rank: the lower rank is, the earlier it executes (upon the same target)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
        # print(name, target, func)
        dest = machine_independent_optimizers
        flags_per_level = mi_flags_per_level
        if is_machine_dependent:
            dest = machine_dependent_optimizers
            flags_per_level = md_flags_per_level
        dest[name] = (func, target, rank)
        flags_per_level[optimize_level].append(name)

        return wrapper
    return decorator

