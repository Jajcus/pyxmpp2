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

import libxml2
import random

import xmlextra
from utils import from_utf8,to_utf8
from types import StringType,UnicodeType
from jid import JID

common_doc=libxml2.newDoc("1.0")
common_root=common_doc.newChild(None,"root",None)

class StanzaError(RuntimeError):
    pass

random.seed()
last_id=random.randrange(1000000)

def gen_id():
    global last_id
    last_id+=1
    return str(last_id)

class Stanza:
    stanza_type="Unknown"
    def __init__(self,name_node,**kw):
        global common_doc
        self.error=None
        self.node=None

        if isinstance(name_node,Stanza):
            self.node=name_node.node.copyNode(1)
            common_doc.addChild(self.node)
        elif isinstance(name_node,libxml2.xmlNode):
            self.node=name_node.docCopyNode(common_doc,1)
            common_doc.addChild(self.node)
            ns=self.node.ns()
            if not ns.name:
                xmlextra.replace_ns(self.node,ns,None)
                xmlextra.remove_ns(self.node,ns)
        else:
            self.node=common_doc.newChild(None,name_node,None)

        if kw.has_key("fr"):
            fr=kw["fr"]
            if fr is not None:
                if not isinstance(fr,JID):
                    fr=JID(fr)
                self.node.setProp("from",fr.as_utf8())
        if kw.has_key("to"):
            to=kw["to"]
            if to is not None:
                if not isinstance(to,JID):
                    to=JID(to)
                self.node.setProp("to",to.as_utf8())
        if kw.has_key("type"):
            typ=kw["type"]
            if typ:
                self.node.setProp("type",kw["type"])
        if kw.has_key("id"):
            id=kw["id"]
            if id:
                self.node.setProp("id",kw["id"])

        if (self.get_type()=="error" and kw.has_key("error_cond")):
            from error import StanzaErrorNode
            self.error=StanzaErrorNode(kw["error_cond"],parent=self.node)

    def __del__(self):
        if self.node:
            self.free()

    def free(self):
        if self.error:
            self.error.free_borrowed()
        self.node.unlinkNode()
        self.node.freeNode()
        self.node=None
        pass

    def copy(self):
        return Stanza(self)

    def serialize(self):
        return self.node.serialize()

    def get_node(self):
        return self.node
    def get_from(self):
        if self.node.hasProp("from"):
            return JID(self.node.prop("from"))
        else:
            return None
    def get_to(self):
        if self.node.hasProp("to"):
            return JID(self.node.prop("to"))
        else:
            return None
    def get_type(self):
        return self.node.prop("type")
    def get_id(self):
        return self.node.prop("id")
    def get_error(self):
        if self.error:
            return self.error
        n=self.node.xpathEval(u"error")
        if not n:
            raise StanzaError,"This stanza contains no error"
        from error import StanzaErrorNode
        self.error=StanzaErrorNode(n[0],copy=0)
        return self.error
    def set_from(self,fr):
        if fr:
            return self.node.setProp("from",to_utf8(fr))
        else:
            return self.node.unsetProp("from")
    def set_to(self,to):
        if to:
            return self.node.setProp("to",to_utf8(to))
        else:
            return self.node.unsetProp("to")
    def set_type(self,type):
        if type:
            return self.node.setProp("type",to_utf8(type))
        else:
            return self.node.unsetProp("type")
    def set_id(self,id):
        if id:
            return self.node.setProp("id",to_utf8(id))
        else:
            return self.node.unsetProp("id")

    def set_content(self,content):
        while self.node.children:
            self.node.children.unlinkNode()
        if isinstance(content,libxml2.xmlNode):
            self.node.addChild(content.docCopyNode(common_doc,1))
        else:
            self.node.setContent(content)

    def add_content(self,content):
        if isinstance(content,libxml2.xmlNode):
            self.node.addChild(content.docCopyNode(common_doc,1))
        else:
            self.node.addContent(content)

    def set_new_content(self,ns_uri,name):
        while self.node.children:
            self.node.children.unlinkNode()
        return self.add_new_content(ns_uri,name)

    def add_new_content(self,ns_uri,name):
        c=self.node.newChild(None,name,None)
        if ns_uri:
            ns=c.newNs(ns_uri,None)
            c.setNs(ns)
        return c

    def xpath_eval(self,expr,namespaces=None):
        if not namespaces:
            return self.node.xpathEval(expr)
        ctxt = common_doc.xpathNewContext()
        ctxt.setContextNode(self.node)
        for prefix,uri in namespaces.items():
            if uri==None:
                uri=COMMON_NS
            ctxt.xpathRegisterNs(prefix,uri)
        ret=ctxt.xpathEval(expr)
        ctxt.xpathFreeContext()
        return ret

    def __eq__(self,other):
        if not isinstance(other,Stanza):
            return 0
        return self.node.serialize()==other.node.serialize();

    def __ne__(self,other):
        if not isinstance(other,Stanza):
            return 1
        return self.node.serialize()!=other.node.serialize();

# vi: sts=4 et sw=4
