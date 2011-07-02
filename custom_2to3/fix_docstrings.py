
from lib2to3 import fixer_base, pytree
from lib2to3.pgen2 import token

def is_docstring(stmt):
    if isinstance(stmt, pytree.Node) and \
            stmt.children[0].type == token.STRING:
                return True
    return None

class FixDocstrings(fixer_base.BaseFix):
    PATTERN = 'simple_stmt' 
    def transform(self, node, results):
        if not is_docstring(node):
            return
        new = node.clone()
        old_s = node.children[0].value
        new_s = old_s.replace("`unicode`", "`str`")
        if old_s == new_s:
            return
        new.children[0].value = new_s
        return new
