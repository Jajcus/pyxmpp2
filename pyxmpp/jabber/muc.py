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
from types import StringType,UnicodeType

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.stanza import common_doc,common_root
from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.iq import Iq
from pyxmpp.jid import JID
from pyxmpp import xmlextra

MUC_NS="http://jabber.org/protocol/muc"
MUC_USER_NS=MUC_NS+"#user"
MUC_ADMIN_NS=MUC_NS+"#admin"
MUC_OWNER_NS=MUC_NS+"#owner"

affiliations=("admin","member","none","outcast","owner")
roles=("moderator","none","participant","visitor")

class MucXBase:
        element="x"
        ns=None
        def __init__(self,node=None,copy=1,parent=None):
                if self.ns==None:
                        raise RuntimeError,"Pure virtual class called"
                self.node=None
                self.borrowed=0
                if isinstance(node,libxml2.xmlNode):
                        if copy:
                                self.node=node.docCopyNode(common_doc,1)
                                common_root.addChild(self.node)
                        else:
                                self.node=node
                                self.borrowed=1
                        if copy:
                                ns=node.ns()
                                xmlextra.replace_ns(self.node,ns,None)
                                xmlextra.remove_ns(self.node,ns)
                elif isinstance(node,MucXBase):
                        if not copy:
                                raise ErrorNodeError,"MucXBase may only be copied"
                        self.node=node.node.docCopyNode(common_doc,1)
                        common_root.addChild(self.node)
                elif node is not None:
                        raise ErrorNodeError,"Bad MucX constructor argument"
                else:
                        if parent:
                                self.node=parent.newChild(None,self.element,None)
                                self.borrowed=1
                        else:
                                self.node=common_root.newChild(None,self.element,None)
                        ns=self.node.newNs(self.ns,None)
                        self.node.setNs(ns)

        def __del__(self):
                if self.node:
                        self.free()

        def free(self):
                if not self.borrowed:
                        self.node.unlinkNode()
                        self.node.freeNode()
                self.node=None

        def free_borrowed(self):
                self.node=None

        def xpath_eval(self,expr):
                ctxt = common_doc.xpathNewContext()
                ctxt.setContextNode(self.node)
                ctxt.xpathRegisterNs("muc",self.ns.getContent())
                ret=ctxt.xpathEval(expr)
                ctxt.xpathFreeContext()
                return ret

        def serialize(self):
                return self.node.serialize()

class MucX(MucXBase):
        ns=MUC_NS
        def __init__(self,node=None,copy=1,parent=None):
                MucXBase.__init__(self,node=None,copy=copy,parent=parent)
        # FIXME: set/get password/history

class MucItemBase:
        def __init__(self):
                raise RuntimeError,"Abstract class called"

class MucItem(MucItemBase):
        def __init__(self,node_or_affiliation,role=None,jid=None,nick=None,actor=None,reason=None):
                if isinstance(node_or_affiliation,libxml2.xmlNode):
                        self.__from_node(node_or_affiliation)
                else:
                        self.__init(node_or_affiliation,role,jid,nick,actor,reason)

        def __init(self,affiliation,role,jid=None,nick=None,actor=None,reason=None):
                if not affiliation:
                        affiliation=None
                elif affiliation not in affiliations:
                        raise ValueError,"Bad affiliation"
                self.affiliation=affiliation
                if not role:
                        role=None
                elif role not in roles:
                        raise ValueError,"Bad role"
                self.role=role
                if jid:
                        self.jid=JID(jid)
                else:
                        self.jid=None
                if actor:
                        self.actor=JID(actor)
                else:
                        self.actor=None
                self.nick=nick
                self.reason=reason

        def __from_node(self,node):
                actor=None
                reason=None
                n=node.children
                while n:
                        ns=n.ns()
                        if ns and ns.getContent()!=MUC_USER_NS:
                                continue
                        if n.name=="actor":
                                actor=n.getContent()
                        if n.name=="reason":
                                reason=n.getContent()
                        n=n.next
                self.__init(
                        from_utf8(node.prop("affiliation")),
                        from_utf8(node.prop("role")),
                        from_utf8(node.prop("jid")),
                        from_utf8(node.prop("nick")),
                        from_utf8(actor),
                        from_utf8(reason),
                        );

        def make_node(self,parent):
                n=parent.newChild(parent.ns(),"item",None)
                if self.actor:
                        n.newTextChild(parent.ns(),"actor",to_utf8(self.actor))
                if self.reason:
                        n.newTextChild(parent.ns(),"reason",to_utf8(self.reason))
                n.setProp("affiliation",to_utf8(self.affiliation))
                n.setProp("role",to_utf8(self.role))
                if self.jid:
                        n.setProp("jid",to_utf8(self.jid.as_unicode()))
                if self.nick:
                        n.setProp("nick",to_utf8(self.nick))
                return n

class MucStatus(MucItemBase):
        def __init__(self,node_or_code):
                if isinstance(node_or_code,libxml2.xmlNode):
                        self.__from_node(node_or_code)
                else:
                        self.__init(node_or_code)

        def __init(self,code):
                code=int(code)
                if code<0 or code>999:
                        raise ValueError,"Bad status code"
                self.code=code

        def __from_node(self,node):
                self.code=int(node.prop("code"))

        def make_node(self,parent):
                n=parent.newChild(parent.ns(),"status",None)
                n.setProp("status","%03i" % (self.code,))
                return n

class MucUserX(MucXBase):
        ns=MUC_USER_NS
        def __init__(self,node=None,copy=1,parent=None):
                MucXBase.__init__(self,node,copy=copy,parent=parent)
        def get_items(self):
                if not self.node.children:
                        return []
                ret=[]
                n=self.node.children
                while n:
                        ns=n.ns()
                        if ns and ns.getContent()!=self.ns:
                                pass
                        elif n.name=="item":
                                ret.append(MucItem(n))
                        elif n.name=="status":
                                ret.append(MucStatus(n))
                        # FIXME: alt,decline,invite,password
                        n=n.next
                return ret
        def clear(self):
                if not self.node.children:
                        return
                n=self.children
                while n:
                        ns=n.ns()
                        if ns and ns.getContent()!=MUC_USER_NS:
                                pass
                        else:
                                n.unlinkNode()
                                n.freeNode()
                        n=n.next
        def add_item(self,item):
                if not isinstance(item,MucItemBase):
                        raise TypeError,"Bad item type for muc#user"
                item.make_node(self.node)

class MucAdminQuery(MucUserX):
        ns=MUC_ADMIN_NS
        element="query"

class MucStanzaExt:
        def __init__(self):
                if not hasattr(self,"node"):
                        raise RuntimeError,"Abstract class called"
                self.muc_child=None

        def get_muc_child(self):
                if self.muc_child:
                        return self.muc_child
                if not self.node.children:
                        return None
                n=self.node.children
                while n:
                        if n.name not in ("x","query"):
                                n=n.next
                                continue
                        ns=n.ns()
                        if not ns:
                                n=n.next
                                continue
                        ns_uri=ns.getContent()
                        if (n.name,ns_uri)==("x",MUC_NS):
                                self.muc_child=MucX(n)
                                return self.muc_child
                        if (n.name,ns_uri)==("x",MUC_USER_NS):
                                self.muc_child=MucUserX(n)
                                return self.muc_child
                        if (n.name,ns_uri)==("query",MUC_ADMIN_NS):
                                self.muc_child=MucAdminQuery(n)
                                return self.muc_child
                        if (n.name,ns_uri)==("query",MUC_OWNER_NS):
                                self.muc_child=MucOwnerX(n)
                                return self.muc_child
                        n=n.next

        def clear_muc_child(self):
                if self.muc_child:
                        self.muc_child.free_borrowed()
                        self.muc_child=None
                if not self.node.children:
                        return
                n=self.node.children
                while n:
                        if n.name not in ("x","query"):
                                n=n.next
                                continue
                        ns=n.ns()
                        if not ns:
                                n=n.next
                                continue
                        ns_uri=ns.getContent()
                        if ns_uri in (MUC_NS,MUC_USER_NS,MUC_ADMIN_NS,MUC_OWNER_NS):
                                n.unlinkNode()
                                n.freeNode()
                        n=n.next

        def make_muc_userinfo(self):
                self.clear_muc_child()
                self.muc_child=MucUserX(parent=self.node)
                return self.muc_child

        def make_muc_admin_quey(self):
                self.clear_muc_child()
                self.muc_child=MucAdminQuery(parent=self.node)
                return self.muc_child

        def muc_free(self):
                if self.muc_child:
                        self.muc_child.free_borrowed()

class MucPresence(Presence,MucStanzaExt):
        def __init__(self,node=None,**kw):
                self.node=None
                MucStanzaExt.__init__(self)
                apply(Presence.__init__,[self,node],kw)

        def copy(self):
                return MucPresence(self)

        def make_join_request(self):
                self.clear_muc_child()
                self.muc_child=MucX(parent=self.node)

        def get_join_info(self):
                x=self.get_muc_child()
                if not x:
                        return None
                if not isinstance(x,MucX):
                        return None
                return x

        def free(self):
                self.muc_free()
                Presence.free(self)

class MucIq(Iq,MucStanzaExt):
        def __init__(self,node=None,**kw):
                self.node=None
                MucStanzaExt.__init__(self)
                apply(Iq.__init__,[self,node],kw)

        def copy(self):
                return MucIq(self)

        def make_kick_request(self,nick,reason):
                self.clear_muc_child()
                self.muc_child=MucAdminQuery(parent=self.node)
                item=MucItem("none","none",nick=nick,reason=reason)
                self.muc_child.add_item(item)
                return self.muc_child

        def free(self):
                self.muc_free()
                Iq.free(self)
# vi: sts=4 et sw=4
