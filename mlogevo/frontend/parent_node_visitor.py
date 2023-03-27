from pycparser.c_ast import NodeVisitor

class ParentNodeVisitor(NodeVisitor):
    def __init__(self):
        self._method_cache = {}
        self.node_stack = []
        self.current_parent = None

        super().__init__()

    def visit(self, node):
        """ Visit a node, while keep a parent node reference in self.current_parent """
        # Almost copy-pasted part from pycparser.c_ast.NodeVisitor
        visitor = self._method_cache.get(node.__class__.__name__, None)
        if visitor is None:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            self._method_cache[node.__class__.__name__] = visitor

        # No, python does NOT have tail call optimization
        # https://stackoverflow.com/questions/13591970/does-python-optimize-tail-recursion
        if len(self.node_stack) > 0:
            self.current_parent = self.node_stack[-1]

        self.node_stack.append(node)
        result = visitor(node)
        self.node_stack.pop()

        return result
