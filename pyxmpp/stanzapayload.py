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
from collections import defaultdict
from xml.etree import ElementTree
import logging

STANZA_PAYLOAD_CLASSES = {}
STANZA_PAYLOAD_ELEMENTS = defaultdict(list)

logger = logging.getLogger("pyxmpp.stanzapayload")

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
        self.xml_element_name = data.tag
        self.element = data

    def as_xml(self):
        return self.element

    @property
    def handler_key(self):
        """Return `self.xml_element_name` as the extra key for stanza
        handlers."""
        return self.xml_element_name

def payload_element_name(element_name):
    """Class decorator generator for decorationg
    `StanzaPayload` subclasses.
    
    :Parameters:
        - `element_name`: XML element qname handled by the class
    :Types:
        - `element_name`: `unicode`
    """
    def decorator(klass):
        if hasattr(klass, "_pyxmpp_payload_element_name"):
            klass._pyxmpp_payload_element_name.append(element_name)
        else:
            klass._pyxmpp_payload_element_name = [element_name]
        if element_name in STANZA_PAYLOAD_CLASSES:
            logger.warning("Overriding payload class for {0!r}".format(
                                                                element_name))
        STANZA_PAYLOAD_CLASSES[element_name] = klass
        STANZA_PAYLOAD_ELEMENTS[klass].append(element_name)
        return klass
    return decorator

def payload_class_for_element_name(element_name):
    logger.debug(" looking up payload class for element: {0!r}".format(
                                                                element_name))
    logger.debug("  known: {0!r}".format(STANZA_PAYLOAD_CLASSES))
    if element_name in STANZA_PAYLOAD_CLASSES:
        return STANZA_PAYLOAD_CLASSES[element_name]
    else:
        return XMLPayload

def payload_element_names_for_class(klass):
    return STANZA_PAYLOAD_ELEMENTS[klass]

def payload_factory(element):
    return payload_class_for_element_name(element.tag)(element)
