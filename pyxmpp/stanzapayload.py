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

"""XMPP payload classes."""

from abc import ABCMeta
from copy import deepcopy
from xml.etree import ElementTree

class StanzaPayload:
    """Abstract base class for stanza payload objects."""
    __metaclass__ = ABCMeta

    def __init__(self, data):
        raise NotImplementedError

    def as_xml(self):
        raise NotImplementedError

    def copy(self):
        return deepcopy(self)

    @property
    def handler_key(self):
        """Defines a key which may be used when registering handlers
        for stanzas with this payload."""
        return None


class XMLPayload(StanzaPayload):
    """Transparent XML payload for stanza.
    
    This object can be used for any stanza payload.
    It doesn't decode the XML element, but instead keeps it in the ElementTree
    format."""
    def __init__(self, data):
        if isinstance(data, StanzaPayload):
            data = data.as_xml()
        if not isinstance(data, ElementTree.Element):
            raise TypeError("ElementTree.Element required")
        if data.tag.startswith("{"):
            self.xml_namespace = data.tag[1:].split("}", 1)[0]
        else:
            self.xml_namespace = None
        self.xml_element_name = data.tag
        self.element = data

    def as_xml(self):
        return self.element

    @property
    def handler_key(self):
        """Return `self.xml_element_name` as the extra key for stanza
        handlers."""
        return self.xml_element_name
    
