#
# (C) Copyright 2003 Jacek Konieczny <jajcus@bnet.pl>
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

"""Utility functions for the pyxmpp package."""

from types import UnicodeType,StringType
import re
import libxml2

def to_utf8(s):
    """
    Convevert `s` to UTF-8 if it is Unicode, leave unchanged 
    if it is string or None and convert to string overwise
    """
    if s is None:
        return None
    elif type(s) is UnicodeType:
        return s.encode("utf-8")
    else:
        return str(s)

def from_utf8(s):
    """
    Convert `s` to Unicode or leave unchanged if it is None.
    
    Regular strings are assumed to be UTF-8 encoded
    """
    if s is None:
        return None
    elif type(s) is UnicodeType:
        return s
    elif type(s) is StringType:
        return unicode(s,"utf-8")
    else:
        return unicode(s)

evil_characters_re=re.compile(r"[\000-\010\013\014\016-\037]",re.UNICODE)
utf8_replacement_char=u"\ufffd".encode("utf-8")
def remove_evil_characters(s):
    """Remove control characters (not allowed in XML) from a string."""
    if type(s) is UnicodeType:
        return evil_characters_re.sub(u"\ufffd",s)
    else:
        return evil_characters_re.sub(utf8_replacement_char,s)

def get_node_ns(node):
    """Return namespace of the XML `node` or None if namespace is not set."""
    try:
        return node.ns()
    except libxml2.treeError:
        return None


def get_node_ns_uri(node):
    """Return namespace URI of the XML `node` or None if namespace is not set."""
    ns=get_node_ns(node)
    if ns:
        return ns.getContent()
    else:
        return None
    
# vi: sts=4 et sw=4
