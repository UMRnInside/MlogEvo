# name: (function, target, rank)
machine_independant_optimizers = {}
machine_dependant_optimizers = {}

# Collect optimizers, has side effects
def register_optimizer(name, target, is_machine_dependant, rank=999):
    """name: in command line, -fremove-unused-labels <-> remove-unused-labels
target: function, basic_block, basic_block_graph
rank: the lower rank is, the earlier it executes (upon the same target)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
        # print(name, target, func)
        dest = machine_independant_optimizers
        if is_machine_dependant:
            dest = machine_dependant_optimizers
        dest[name] = (func, target, rank)

        return wrapper
    return decorator

