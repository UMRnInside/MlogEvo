from pycparser.c_ast import NodeVisitor

class ParentNodeVisitor(NodeVisitor):
    def __init__(self):
        self._method_cache = {}
        self.current_parent = None

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
        old_parent = self.current_parent
        self.current_parent = node
        result = visitor(node)
        self.current_parent = old_parent

        return result
