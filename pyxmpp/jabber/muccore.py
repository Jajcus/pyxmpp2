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
"""Jabber Multi-User Chat implementation.

Normative reference:
  - `JEP 45 <http://www.jabber.org/jeps/jep-0045.html>`__
"""

__revision__="$Id: muc.py,v 1.27 2004/10/07 22:28:11 jajcus Exp $"
__docformat__="restructuredtext en"

import libxml2

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.stanza import common_doc,common_root
from pyxmpp.presence import Presence
from pyxmpp.error import ErrorNodeError
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
    """
    Base class for MUC-specific stanza payload - wrapper around
    an XML node.

    :Ivariables:
        - `node`: the wrapped XML node
    """
    element="x"
    ns=None
    def __init__(self,node=None,copy=True,parent=None):
        """
        Copy MucXBase object or create a new one, possibly
        based on or wrappin an XML node.

        `node` is a MucXBase instance to compy or an XML node
        When `copy` is False this MucXBase will wrap existing
        XML node (e.g. part of a stanza), the XML node will be
        copied otherwise.
        If `parent` is not `None` it will be the parent of newly created node
        node
        """
        if self.ns==None:
            raise RuntimeError,"Pure virtual class called"
        self.node=None
        self.borrowed=False
        if isinstance(node,libxml2.xmlNode):
            if copy:
                self.node=node.docCopyNode(common_doc,1)
                common_root.addChild(self.node)
            else:
                self.node=node
                self.borrowed=True
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
                self.borrowed=True
            else:
                self.node=common_root.newChild(None,self.element,None)
            ns=self.node.newNs(self.ns,None)
            self.node.setNs(ns)

    def __del__(self):
        if self.node:
            self.free()

    def free(self):
        """
        Unlink and free the XML node owned by `self`.
        """
        if not self.borrowed:
            self.node.unlinkNode()
            self.node.freeNode()
        self.node=None

    def free_borrowed(self):
        """
        Detach the XML node borrowed by `self`.
        """
        self.node=None

    def xpath_eval(self,expr):
        """
        Evaluate XPath expression in context of `self.node`
        """
        ctxt = common_doc.xpathNewContext()
        ctxt.setContextNode(self.node)
        ctxt.xpathRegisterNs("muc",self.ns.getContent())
        ret=ctxt.xpathEval(expr)
        ctxt.xpathFreeContext()
        return ret

    def serialize(self):
        """
        Serialize `self` as XML.
        """
        return self.node.serialize()

class MucX(MucXBase):
    """
    Wrapper for http://www.jabber.org/protocol/muc namespaced
    stanza payload "x" elements.
    """
    ns=MUC_NS
    def __init__(self,node=None,copy=True,parent=None):
        MucXBase.__init__(self,node=node,copy=copy,parent=parent)
    # FIXME: set/get password/history

class MucItemBase:
    """
    Base class for <status/> and <item/> element wrappers.
    """
    def __init__(self):
        if self.__class__ is MucItemBase:
            raise RuntimeError,"Abstract class called"

class MucItem(MucItemBase):
    """
    MUC <item/> element - describes a room occupant.

    Public attributes:
    - affiliation
    - role
    - jid
    - nick
    - actor
    - reason
    (all described in JEP-45)
    """
    def __init__(self,node_or_affiliation,role=None,jid=None,nick=None,actor=None,reason=None):
        """
        Initialize `self` from `libxml2.xmlNode` instance or a set of
        attributes.
        """
        self.jid,self.nick,self.actor,self.affiliation,self.reason,self.role=(None,)*6
        MucItemBase.__init__(self)
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

    def as_xml(self,parent):
        """
        Create `libxml2.xmlNode` representation of `self`.

        `parent` is the element to which the created node should be linked to.
        """
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
    """
    MUC <item/> element - describes special meaning of a stanza

    Public attributes:
    - code (as described in JEP-45)
    """
    def __init__(self,node_or_code):
        """
        Initialize `self` from `libxml2.xmlNode` instance or a code number.

        """
        self.code=None
        MucItemBase.__init__(self)
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

    def as_xml(self,parent):
        """
        Create `libxml2.xmlNode` representation of `self`.

        `parent` is the element to which the created node should be linked to.
        """
        n=parent.newChild(parent.ns(),"status",None)
        n.setProp("code","%03i" % (self.code,))
        return n

class MucUserX(MucXBase):
    """
    Wrapper for http://www.jabber.org/protocol/muc#user namespaced
    stanza payload "x" elements and usually containing information
    about a room user.

    :Ivariables:
        - `node`: wrapped XML node
    """
    ns=MUC_USER_NS
    def get_items(self):
        """
        Return a list of MucItem and MucStatus and similar objects describing
        the content of `self`.
        """
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
        """
        Clear the content of `self.node` removing all <item/>, <status/>, etc.
        """
        if not self.node.children:
            return
        n=self.node.children
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
        item.as_xml(self.node)

class MucOwnerX(MucXBase):
    """
    Wrapper for http://www.jabber.org/protocol/muc#owner namespaced
    stanza payload "x" elements and usually containing information
    about a room user.

    :Ivariables:
        - `node`: wrapped XML node
    """
    # FIXME: implement
    pass

class MucAdminQuery(MucUserX):
    """
    Wrapper for http://www.jabber.org/protocol/muc#admin namespaced
    IQ stanza payload "query" elements and usually describing
    administrative actions or their results.

    Not implemented yet.
    """
    ns=MUC_ADMIN_NS
    element="query"

class MucStanzaExt:
    """
    Base class for MUC specific stanza extensions. Used together
    with one of stanza classes (Iq, Message or Presence).
    """
    def __init__(self):
        if self.__class__ is MucStanzaExt:
            raise RuntimeError,"Abstract class called"
        self.node=None
        self.muc_child=None

    def get_muc_child(self):
        """
        Return the MUC specific payload element.
        """
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
        """
        Remove the MUC specific stanza payload element.
        """
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
        """
        Create <x xmlns="...muc#user"/> element in the stanza.
        """
        self.clear_muc_child()
        self.muc_child=MucUserX(parent=self.node)
        return self.muc_child

    def make_muc_admin_quey(self):
        """
        Create <query xmlns="...muc#admin"/> element in the stanza.
        """
        self.clear_muc_child()
        self.muc_child=MucAdminQuery(parent=self.node)
        return self.muc_child

    def muc_free(self):
        """
        Free MUC specific data.
        """
        if self.muc_child:
            self.muc_child.free_borrowed()

class MucPresence(Presence,MucStanzaExt):
    """
    Extend `Presence` with MUC related interface.
    """
    def __init__(self,node=None,from_jid=None,to_jid=None,stanza_type=None,stanza_id=None,
            show=None,status=None,priority=0,error=None,error_cond=None):
        """
        Initialize `self` from an XML node or a set of attributes.

        See `Presence.__init__` for allowed keyword arguments.
        """
        MucStanzaExt.__init__(self)
        Presence.__init__(self,node,from_jid=from_jid,to_jid=to_jid,
                stanza_type=stanza_type,stanza_id=stanza_id,
                show=show,status=status,priority=priority,
                error=error,error_cond=error_cond)

    def copy(self):
        """
        Return a copy of `self`.
        """
        return MucPresence(self)

    def make_join_request(self):
        """
        Make the presence stanza a MUC room join request.
        """
        self.clear_muc_child()
        self.muc_child=MucX(parent=self.node)

    def get_join_info(self):
        """
        If `self` is a MUC room join request return information contained
        (as `MucX` object), return None otherwise.
        """
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
    """
    Extend `Iq` with MUC related interface.
    """
    def __init__(self,node=None,from_jid=None,to_jid=None,stanza_type=None,stanza_id=None,
            error=None,error_cond=None):
        """
        Initialize `self` from an XML node or a set of attributes.

        See `Presence.__init__` for allowed keyword arguments.
        """
        MucStanzaExt.__init__(self)
        Iq.__init__(self,node,from_jid=from_jid,to_jid=to_jid,
                stanza_type=stanza_type,stanza_id=stanza_id,
                error=error,error_cond=error_cond)

    def copy(self):
        """
        Return a copy of `self`.
        """
        return MucIq(self)

    def make_kick_request(self,nick,reason):
        """
        Make the iq stanza a MUC room participant kick request.
        """
        self.clear_muc_child()
        self.muc_child=MucAdminQuery(parent=self.node)
        item=MucItem("none","none",nick=nick,reason=reason)
        self.muc_child.add_item(item)
        return self.muc_child

    def free(self):
        self.muc_free()
        Iq.free(self)

# vi: sts=4 et sw=4
