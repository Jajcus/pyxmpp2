"""
Taken from: http://lucumr.pocoo.org/2010/2/11/porting-to-python-3-a-guide/
"""
from lib2to3 import fixer_base
from lib2to3.fixer_util import Name

class FixRenameUnicode(fixer_base.BaseFix):
    PATTERN = r"funcdef< 'def' name='__unicode__' parameters< '(' NAME ')' > any+ >"

    def transform(self, node, results):
        name = results['name']
        name.replace(Name('__str__', prefix=name.prefix))
