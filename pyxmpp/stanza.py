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

"""General XMPP Stanza handling."""

__revision__="$Id: stanza.py,v 1.18 2004/09/14 19:57:58 jajcus Exp $"
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
          the stanza of type "error"."""
    stanza_type="Unknown"

    def __init__(self,name_or_node,fr=None,to=None,typ=None,sid=None,
                error=None,error_cond=None):
        """Initialize a Stanza object.

        :Parameters:
            - `name_or_node`: XML node to be wrapped into the Stanza object
              or other Presence object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `fr`: sender JID.
            - `to`: recipient JID.
            - `typ`: staza type: one of: "get", "set", "result" or "error".
            - `sid`: stanza id -- value of stanza's "id" attribute. If not
              given, then unique for the session value is generated. 
            - `error_cond`: error condition name. Ignored if `typ` is not "error". """


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

        if fr is not None:
            if not isinstance(fr,JID):
                fr=JID(fr)
            self.node.setProp("from",fr.as_utf8())
        
        if to is not None:
            if not isinstance(to,JID):
                to=JID(to)
            self.node.setProp("to",to.as_utf8())
            
        if typ:
            self.node.setProp("type",typ)
            
        if sid:
            self.node.setProp("id",sid)

        if (self.get_type()=="error" and error_cond):
            from pyxmpp.error import StanzaErrorNode
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
        """Create a deep copy of the stanza."""
        return Stanza(self)

    def serialize(self):
        """Serialize the stanza into a XML string.
        
        :return: serialized stanza."""
        return self.node.serialize()

    def get_node(self):
        """Return XML node wrapped into `self`."""
        return self.node
        
    def get_from(self):
        """Get "from" attribute of the stanza.
        
        :return: value of the "from" attribute (sender JID) or None."""
        if self.node.hasProp("from"):
            return JID(from_utf8(self.node.prop("from")))
        else:
            return None
            
    def get_to(self):
        """Get "to" attribute of the stanza.
        
        :return: value of the "to" attribute (recipient JID) or None."""
        if self.node.hasProp("to"):
            return JID(from_utf8(self.node.prop("to")))
        else:
            return None
            
    def get_type(self):
        """Get "type" attribute of the stanza.
        
        :return: value of the "type" attribute (stanza type) or None."""
        if self.node.hasProp("type"):
            return from_utf8(self.node.prop("type"))
        else:
            return None

    def get_id(self):
        """Get "id" attribute of the stanza.
        
        :return: value of the "id" attribute (stanza identifier) or None."""
        if self.node.hasProp("id"):
            return from_utf8(self.node.prop("id"))
        else:
            return None
        
    def get_error(self):
        """Get stanza error information.

        :return: `pyxmpp.error.StanzaErrorNode` object describing the error."""
        if self._error:
            return self._error
        n=self.node.xpathEval(u"error")
        if not n:
            raise StanzaError,"This stanza contains no error"
        from pyxmpp.error import StanzaErrorNode
        self._error=StanzaErrorNode(n[0],copy=0)
        return self._error
        
    def set_from(self,fr):
        """Set "from" attribute of the stanza.
        
        :Parameters:
            - `fr`: new value of the "from" attribute (sender JID)."""
        if fr:
            return self.node.setProp("from",to_utf8(fr))
        else:
            return self.node.unsetProp("from")

    def set_to(self,to):
        """Set "to" attribute of the stanza.
        
        :Parameters:
            - `to`: new value of the "to" attribute (recipient JID)."""
        if to:
            return self.node.setProp("to",to_utf8(to))
        else:
            return self.node.unsetProp("to")
            
    def set_type(self,typ):
        """Set "type" attribute of the stanza.
        
        :Parameters:
            - `typ`: new value of the "type" attribute (stanza type)."""
        if typ:
            return self.node.setProp("type",to_utf8(typ))
        else:
            return self.node.unsetProp("type")
            
    def set_id(self,sid):
        """Set "id" attribute of the stanza.
        
        :Parameters:
            - `sid`: new value of the "id" attribute (stanza identifier)."""
        if sid:
            return self.node.setProp("id",to_utf8(sid))
        else:
            return self.node.unsetProp("id")

    def set_content(self,content):
        """Set stanza content to an XML node.

        :Parameters:
            - `content`: XML node to be included in the stanza.
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
        """
        while self.node.children:
            self.node.children.unlinkNode()
        return self.add_new_content(ns_uri,name)

    def add_new_content(self,ns_uri,name):
        """Add a new XML element to the stanza payload.

        :Parameters:
            - `ns_uri`: XML namespace URI of the element.
            - `name`: element name.
        """
        c=self.node.newChild(None,name,None)
        if ns_uri:
            ns=c.newNs(ns_uri,None)
            c.setNs(ns)
        return c

    def xpath_eval(self,expr,namespaces=None):
        """Evaluate an XPath expression on the stanza XML node.

        :Parameters:
            - `expr`: XPath expression.
            - `namespaces`: mapping from namespace prefixes to URIs.
        """
        if not namespaces:
            return self.node.xpathEval(expr)
        ctxt = common_doc.xpathNewContext()
        ctxt.setContextNode(self.node)
        for prefix,uri in namespaces.items():
            ctxt.xpathRegisterNs(prefix,uri)
        ret=ctxt.xpathEval(expr)
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
