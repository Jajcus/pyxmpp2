#
# (C) Copyright 2003-2004 Jacek Konieczny <jajcus@jajcus.net>
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

__revision__="$Id$"
__docformat__="restructuredtext en"

import libxml2
import random

from pyxmpp import xmlextra
from pyxmpp.utils import from_utf8,to_utf8
from pyxmpp.jid import JID

common_doc=libxml2.newDoc("1.0")
common_root=common_doc.newChild(None,"root",None)

class StanzaError(ValueError):
    """Raised on ivalid stanza objects usage."""
    pass

random.seed()
last_id=random.randrange(1000000)

def gen_id():
    """Generate stanza id unique for the session.

    :return: the new id."""
    global last_id
    last_id+=1
    return str(last_id)

class Stanza:
    """Base class for all XMPP stanzas.

    :Ivariables:
        - `node`: stanza XML node.
        - `_error`: `pyxmpp.error.StanzaErrorNode` describing the error associated with
          the stanza of type "error".
    :Types:
        - `node`: `libxml2.xmlNode`
        - `_error`: `pyxmpp.error.StanzaErrorNode`"""
    stanza_type="Unknown"

    def __init__(self, name_or_node, from_jid=None, to_jid=None,
            stanza_type=None, stanza_id=None, error=None, error_cond=None):
        """Initialize a Stanza object.

        :Parameters:
            - `name_or_node`: XML node to be wrapped into the Stanza object
              or other Presence object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `from_jid`: sender JID.
            - `to_jid`: recipient JID.
            - `stanza_type`: staza type: one of: "get", "set", "result" or "error".
            - `stanza_id`: stanza id -- value of stanza's "id" attribute. If
              not given, then unique for the session value is generated.
            - `error`: error object. Ignored if `stanza_type` is not "error".
            - `error_cond`: error condition name. Ignored if `stanza_type` is not
              "error" or `error` is not None.
        :Types:
            - `name_or_node`: `unicode` or `libxml2.xmlNode` or `Stanza`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `error`: `pyxmpp.error.StanzaErrorNode`
            - `error_cond`: `unicode`"""
        self._error=None
        self.node=None
        if isinstance(name_or_node,Stanza):
            self.node=name_or_node.node.copyNode(1)
            common_doc.addChild(self.node)
        elif isinstance(name_or_node,libxml2.xmlNode):
            self.node=name_or_node.docCopyNode(common_doc,1)
            common_doc.addChild(self.node)
            ns=self.node.ns()
            if not ns.name:
                xmlextra.replace_ns(self.node,ns,None)
                xmlextra.remove_ns(self.node,ns)
        else:
            self.node=common_doc.newChild(None,name_or_node,None)

        if from_jid is not None:
            if not isinstance(from_jid,JID):
                from_jid=JID(from_jid)
            self.node.setProp("from",from_jid.as_utf8())

        if to_jid is not None:
            if not isinstance(to_jid,JID):
                to_jid=JID(to_jid)
            self.node.setProp("to",to_jid.as_utf8())

        if stanza_type:
            self.node.setProp("type",stanza_type)

        if stanza_id:
            self.node.setProp("id",stanza_id)

        if self.get_type()=="error":
            from pyxmpp.error import StanzaErrorNode
            if error:
                self._error=StanzaErrorNode(error,parent=self.node,copy=1)
            elif error_cond:
                self._error=StanzaErrorNode(error_cond,parent=self.node)

    def __del__(self):
        if self.node:
            self.free()

    def free(self):
        """Free the node associated with this `Stanza` object."""
        if self._error:
            self._error.free_borrowed()
        self.node.unlinkNode()
        self.node.freeNode()
        self.node=None

    def copy(self):
        """Create a deep copy of the stanza.

        :returntype: `Stanza`"""
        return Stanza(self)

    def serialize(self):
        """Serialize the stanza into an UTF-8 encoded XML string.

        :return: serialized stanza.
        :returntype: `str`"""
        return self.node.serialize(encoding="utf-8")

    def get_node(self):
        """Return the XML node wrapped into `self`.

        :returntype: `libxml2.xmlNode`"""
        return self.node

    def get_from(self):
        """Get "from" attribute of the stanza.

        :return: value of the "from" attribute (sender JID) or None.
        :returntype: `unicode`"""
        if self.node.hasProp("from"):
            return JID(from_utf8(self.node.prop("from")))
        else:
            return None

    def get_to(self):
        """Get "to" attribute of the stanza.

        :return: value of the "to" attribute (recipient JID) or None.
        :returntype: `unicode`"""
        if self.node.hasProp("to"):
            return JID(from_utf8(self.node.prop("to")))
        else:
            return None

    def get_type(self):
        """Get "type" attribute of the stanza.

        :return: value of the "type" attribute (stanza type) or None.
        :returntype: `unicode`"""
        if self.node.hasProp("type"):
            return from_utf8(self.node.prop("type"))
        else:
            return None

    def get_id(self):
        """Get "id" attribute of the stanza.

        :return: value of the "id" attribute (stanza identifier) or None.
        :returntype: `unicode`"""
        if self.node.hasProp("id"):
            return from_utf8(self.node.prop("id"))
        else:
            return None

    def get_error(self):
        """Get stanza error information.

        :return: object describing the error.
        :returntype: `pyxmpp.error.StanzaErrorNode`"""
        if self._error:
            return self._error
        n=self.node.xpathEval(u"error")
        if not n:
            raise StanzaError,"This stanza contains no error"
        from pyxmpp.error import StanzaErrorNode
        self._error=StanzaErrorNode(n[0],copy=0)
        return self._error

    def set_from(self,from_jid):
        """Set "from" attribute of the stanza.

        :Parameters:
            - `from_jid`: new value of the "from" attribute (sender JID).
        :Types:
            - `from_jid`: `unicode`"""
        if from_jid:
            return self.node.setProp("from",to_utf8(from_jid))
        else:
            return self.node.unsetProp("from")

    def set_to(self,to_jid):
        """Set "to" attribute of the stanza.

        :Parameters:
            - `to_jid`: new value of the "to" attribute (recipient JID).
        :Types:
            - `to_jid`: `unicode`"""
        if to_jid:
            return self.node.setProp("to",to_utf8(to_jid))
        else:
            return self.node.unsetProp("to")

    def set_type(self,stanza_type):
        """Set "type" attribute of the stanza.

        :Parameters:
            - `stanza_type`: new value of the "type" attribute (stanza type).
        :Types:
            - `stanza_type`: `unicode`"""
        if stanza_type:
            return self.node.setProp("type",to_utf8(stanza_type))
        else:
            return self.node.unsetProp("type")

    def set_id(self,stanza_id):
        """Set "id" attribute of the stanza.

        :Parameters:
            - `stanza_id`: new value of the "id" attribute (stanza identifier).
        :Types:
            - `stanza_id`: `unicode`"""
        if stanza_id:
            return self.node.setProp("id",to_utf8(stanza_id))
        else:
            return self.node.unsetProp("id")

    def set_content(self,content):
        """Set stanza content to an XML node.

        :Parameters:
            - `content`: XML node to be included in the stanza.
        :Types:
            - `content`: `libxml2.xmlNode` or UTF-8 `str`
        """
        while self.node.children:
            self.node.children.unlinkNode()
        if isinstance(content,libxml2.xmlNode):
            self.node.addChild(content.docCopyNode(common_doc,1))
        else:
            self.node.setContent(content)

    def add_content(self,content):
        """Add an XML node to the stanza's payload.

        :Parameters:
            - `content`: XML node to be added to the payload.
        :Types:
            - `content`: `libxml2.xmlNode` or UTF-8 `str`
        """
        if isinstance(content,libxml2.xmlNode):
            self.node.addChild(content.docCopyNode(common_doc,1))
        else:
            self.node.addContent(content)

    def set_new_content(self,ns_uri,name):
        """Set stanza payload to a new XML element.

        :Parameters:
            - `ns_uri`: XML namespace URI of the element.
            - `name`: element name.
        :Types:
            - `ns_uri`: `str`
            - `name`: `str` or `unicode`
        """
        while self.node.children:
            self.node.children.unlinkNode()
        return self.add_new_content(ns_uri,name)

    def add_new_content(self,ns_uri,name):
        """Add a new XML element to the stanza payload.

        :Parameters:
            - `ns_uri`: XML namespace URI of the element.
            - `name`: element name.
        :Types:
            - `ns_uri`: `str`
            - `name`: `str` or `unicode`
        """
        c=self.node.newChild(None,to_utf8(name),None)
        if ns_uri:
            ns=c.newNs(ns_uri,None)
            c.setNs(ns)
        return c

    def xpath_eval(self,expr,namespaces=None):
        """Evaluate an XPath expression on the stanza XML node.

        :Parameters:
            - `expr`: XPath expression.
            - `namespaces`: mapping from namespace prefixes to URIs.
        :Types:
            - `expr`: `unicode`
            - `namespaces`: `dict` or other mapping
        """
        if not namespaces:
            return self.node.xpathEval(to_utf8(expr))
        ctxt = common_doc.xpathNewContext()
        ctxt.setContextNode(self.node)
        for prefix,uri in namespaces.items():
            ctxt.xpathRegisterNs(to_utf8(prefix),uri)
        ret=ctxt.xpathEval(to_utf8(expr))
        ctxt.xpathFreeContext()
        return ret

    def __eq__(self,other):
        if not isinstance(other,Stanza):
            return False
        return self.node.serialize()==other.node.serialize()

    def __ne__(self,other):
        if not isinstance(other,Stanza):
            return True
        return self.node.serialize()!=other.node.serialize()

# vi: sts=4 et sw=4
