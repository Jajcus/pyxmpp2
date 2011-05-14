#
# (C) Copyright 2003-2011 Jacek Konieczny <jajcus@jajcus.net>
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

"""General XMPP Stanza handling.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

from __future__ import absolute_import

__docformat__="restructuredtext en"

from xml.etree import ElementTree
import random
import weakref
import copy

from .exceptions import ProtocolError, JIDMalformedProtocolError
from .jid import JID
from .stanzapayload import StanzaPayload, XMLPayload
from .xmppserializer import serialize

random.seed()
last_id = random.randrange(1000000)

def gen_id():
    """Generate stanza id unique for the session.

    :return: the new id."""
    global last_id
    last_id += 1
    return str(last_id)

class Stanza(object):
    """Base class for all XMPP stanzas.

    :Properties:
        - `from_jid`: source JID of the stanza
        - `to_jid`: destination JID of the stanza
        - `stanza_type`: staza type: one of: "get", "set", "result" or "error".
        - `stanza_id`: stanza id
        - `stream`: stream on which the stanza was received or `None` when the
          stream is not available. May be used to send replies or get some
          session-related parameters.
    :Ivariables:
        - `_payload`: the stanza payload
        - `_error`: error associated a stanza of type "error"
        - `_namespace`: namespace of this stanza element
    :Types:
        - `from_jid`: `JID`
        - `to_jid`: `JID`
        - `stanza_type`: `unicode`
        - `stanza_id`: `unicode`
        - `stream`: `pyxmpp2.stream.Stream`
        - `_payload`: `list` of `StanzaPayload`
        - `_error`: `pyxmpp2.error.StanzaErrorElement`"""
    element_name = "Unknown"
    def __init__(self, element, from_jid = None, to_jid = None,
                            stanza_type = None, stanza_id = None,
                            error = None, error_cond = None,
                            stream = None):
        """Initialize a Stanza object.

        :Parameters:
            - `element`: XML element of this stanza, or element name for a new
              stanza. If element is given it must not be modified later,
              unless `decode_payload()` and `mark_dirty()` methods are called
              first.
            - `from_jid`: sender JID.
            - `to_jid`: recipient JID.
            - `stanza_type`: staza type: one of: "get", "set", "result" 
                                                                or "error".
            - `stanza_id`: stanza id -- value of stanza's "id" attribute. If
              not given, then unique for the session value is generated.
            - `error`: error object. Ignored if `stanza_type` is not "error".
            - `error_cond`: error condition name. Ignored if `stanza_type` is
              not "error" or `error` is not None.
        :Types:
            - `_element`: `unicode` or `ElementTree.Element`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `error`: `pyxmpp.error.StanzaErrorElement`
            - `error_cond`: `unicode`"""
        self._error = None
        self._from_jid = None
        self._to_jid = None
        self._stanza_type = None
        self._stanza_id = None
        if isinstance(element, ElementTree.Element):
            self._element = element
            self._dirty = False
            self._decode_attributes()
            if element.tag.startswith("{"):
                self._namespace, self.element_name = element.tag[1:].split("}")
            else:
                self._namespace = "jabber:client"
                self.element_name = element.tag
            self._payload = None
        else:
            self._element = None
            self._dirty = True
            self.element_name = unicode(element)
            self._namespace = "jabber:client"
            self._payload = []

        self._ns_prefix = "{{{0}}}".format(self._namespace)
        self._element_qname = self._ns_prefix + self.element_name

        if from_jid is not None:
            self.from_jid = from_jid

        if to_jid is not None:
            self.to_jid = to_jid

        if stanza_type:
            self.stanza_type = stanza_type

        if stanza_id:
            self.stanza_id = stanza_id

        if self.stanza_type == "error":
            from .error import StanzaErrorElement
            if error:
                self._error = StanzaErrorElement(error)
            elif error_cond:
                self._error = StanzaErrorElement(error_cond)

        if stream is not None:
                self._stream = weakref.ref(stream)
    
    def _decode_attributes(self):
        from_jid = self._element.get('from')
        if from_jid:
            self._from_jid = JID(from_jid)
        to_jid = self._element.get('to')
        if to_jid:
            self._to_jid = JID(to_jid)
        self._stanza_type = self._element.get('type')
        self._stanza_id = self._element.get('id')

    def copy(self):
        """Create a deep copy of the stanza.

        :returntype: `Stanza`"""
        result = Stanza(self.element_name, self.from_jid, self.to_jid, 
                        self.stanza_type, self.stanza_id, self.error,
                        self.stream)
        for payload in self._payload:
            result.add_payload(payload.copy())
        return result

    def serialize(self):
        """Serialize the stanza into an UTF-8 encoded XML string.

        :return: serialized stanza.
        :returntype: `str`"""
        return serialize(self.get_xml())

    def as_xml(self):
        """Return the XML stanza representation.

        Always return an independent copy of the stanza XML representation,
        which can be freely modified without affecting the stanza.

        :returntype: `ElementTree.Element`"""
        attrs = {}
        if self._from_jid:
            attrs['from'] = unicode(self._from_jid)
        if self._to_jid:
            attrs['to'] = unicode(self._to_jid)
        if self._stanza_type:
            attrs['type'] = self._stanza_type
        if self._stanza_id:
            attrs['id'] = self._stanza_id
        element = ElementTree.Element(self._element_qname, attrs)
        if self._payload is None:
            self.decode_payload()
        for payload in self._payload:
            element.append(payload.as_xml())
        return element

    def get_xml(self):
        """Return the XML stanza representation.

        This returns the original or cached XML representation, which
        may be much more efficient than `as_xml`. 
        
        Result of this function should never be modified.

        :returntype: `ElementTree.Element`"""
        if not self._dirty:
            return self._element
        element = self.as_xml()
        self._element = element
        self._dirty = False
        return element

    def decode_payload(self):
        """Decode payload from the element passed to the stanza constructor.

        Iterates over stanza children and creates StanzaPayload objects for
        them. Called automatically by `get_payload()` and other methods that
        access the payload.
        
        For the `Stanza` class stanza namespace child elements will also be
        included as the payload. For subclasses these are not considered
        payload."""
        if self._payload is not None:
            # already decoded
            return
        if self._element is None:
            raise ValueError, "This stanza has no element to decode"""
        payload = []
        for child in self._element:
            if self.__class__ is not Stanza:
                if child.tag.startswith(self._ns_prefix):
                    continue
            payload.append(XMLPayload(child))
        self._payload = payload

    @property
    def from_jid(self):
        return self._from_jid

    @from_jid.setter
    def from_jid(self, from_jid):
        self._from_jid = JID(from_jid)
        self._dirty = True

    @property
    def to_jid(self):
        return self._to_jid

    @to_jid.setter
    def to_jid(self, to_jid):
        self._to_jid = JID(to_jid)
        self._dirty = True

    @property
    def stanza_type(self):
        return self._stanza_type

    @stanza_type.setter
    def stanza_type(self, stanza_type):
        self._stanza_type = unicode(stanza_type)
        self._dirty = True

    @property
    def stanza_id(self):
        return self._stanza_id

    @stanza_id.setter
    def stanza_id(self, stanza_id):
        self._stanza_id = unicode(stanza_id)
        self._dirty = True

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, error):
        self._error = error
        self._dirty = True

    def mark_dirty(self):
        """Mark the stanza `dirty` so the XML representation will be
        re-built the next time it is requested.
        
        This should be called each time the payload attached to the stanza is
        modifed."""
        self._dirty = True

    def set_payload(self, payload):
        """Set stanza payload to a single item. 
        
        All current stanza content of will be dropped.
        Marks the stanza dirty.

        :Parameters:
            - `payload`: XML element or stanza payload object to use
        :Types:
            - `payload`: `ElementTree.Element` or `StanzaPayload`
        """
        if isinstance(payload, ElementTree.Element):
            self._payload = [ XMLPayload(payload) ]
        elif isinstance(payload, StanzaPayload):
            self._payload = [ payload ]
        else:
            raise TypeError, "Bad payload type"
        self._dirty = True

    def add_payload(self, payload):
        """Add new the stanza payload.
        
        Marks the stanza dirty.

        :Parameters:
            - `payload`: XML element or stanza payload object to add
        :Types:
            - `payload`: `ElementTree.Element` or `StanzaPayload`
        """
        if self._payload is None:
            self.decode_payload()
        if isinstance(payload, ElementTree.Element):
            self._payload.append(XMLPayload(payload))
        elif isinstance(payload, StanzaPayload):
            self._payload.append(payload)
        else:
            raise TypeError, "Bad payload type"
        self._dirty = True

    def get_all_payload(self):
        """Return list of stanza payload objects.
       
        :Returntype: `list` of `StanzaPayload`
        """
        if self._payload is None:
            self.decode_payload()
        return list(self._payload)

#    def __eq__(self, other):
#        if not isinstance(other,Stanza):
#            return False

# vi: sts=4 et sw=4
