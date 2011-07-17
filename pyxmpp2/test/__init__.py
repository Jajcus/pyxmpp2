#
# (C) Copyright 2011 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

"""PyXMPP2 test suite."""

import os
import unittest

try:
    import pyxmpp2.etree
    if "PYXMPP2_ETREE" not in os.environ:
        # one of tests fails when xml.etree.ElementTree is used
        import xml.etree.cElementTree
        pyxmpp2.etree.ElementTree = xml.etree.cElementTree
except ImportError:
    pass

def discover():
    """Discover all the test suites in pyxmpp2.test."""
    suite = unittest.TestSuite()
    for mod in unittest.defaultTestLoader.discover("pyxmpp2.test", "[a-z]*.py"):
        suite.addTest(mod)
    return suite

