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

"""ElementTree API selection.

The rest of PyXMPP2 package imports the ElementTree API from this module.

The actual API can be selected in one of two ways:

By importing this module (before anything else) its `ElementTree` variable:

    >> import pyxmpp2.etree
    >> import xml.etree.cElementTree
    >> pyxmpp2.etree.ElementTree = xml.etree.cElementTree

Or by setting the 'PYXMPP2_ETREE' variable, e.g.:

    $ PYXMPP2_ETREE="xml.etree"


By default the standard Python ElementTree implementation is used
(`xml.etree.ElementTree`)
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import os
from abc import ABCMeta

if "PYXMPP2_ETREE" in os.environ:
    ElementTree = __import__(os.environ["PYXMPP2_ETREE"], fromlist=[""])
else:
    from xml.etree import ElementTree

class ElementClass:
    __metaclass__ = ABCMeta
    element_type = type(ElementTree.Element("x"))
    @classmethod
    def __subclasshook__(cls, other):
        if cls is ElementClass:
            return other is cls.element_type or hasattr(other, "tag")
        return NotImplemented

