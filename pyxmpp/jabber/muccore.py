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

__revision__="$Id$"
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
    an XML element.

    :Ivariables:
        - `node`: the wrapped XML node
    """
    element="x"
    ns=None
    def __init__(self,node=None,copy=True,parent=None):
        """
        Copy MucXBase object or create a new one, possibly
        based on or wrapping an XML node.
        
        :Parameters:
            - `node`: is the object to copy or an XML node to wrap.
            - `copy`: when `True` a copy of the XML node provided will be included
              in `self`, the node will be copied otherwise.
            - `parent`: parent node for the created/copied XML element.
        :Types:
            - `node`: `MucXBase` or `libxml2.xmlNode`
            - `copy`: `bool`
            - `parent`: `libxml2.xmlNode`
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
        Evaluate XPath expression in context of `self.node`.

        :Parameters:
            - `expr`: the XPath expression
        :Types:
            - `expr`: `unicode`

        :return: the result of the expression evaluation.
        :returntype: list of `libxml2.xmlNode`
        """
        ctxt = common_doc.xpathNewContext()
        ctxt.setContextNode(self.node)
        ctxt.xpathRegisterNs("muc",self.ns.getContent())
        ret=ctxt.xpathEval(to_utf8(expr))
        ctxt.xpathFreeContext()
        return ret

    def serialize(self):
        """
        Serialize `self` as XML.

        :return: serialized `self.node`.
        :returntype: `str`
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
    MUC <item/> element -- describes a room occupant.

    :Ivariables:
        - `affiliation`: affiliation of the user.
        - `role`: role of the user.
        - `jid`: JID of the user.
        - `nick`: nickname of the user.
        - `actor`: actor modyfying the user data.
        - `reason`: reason of change of the user data.
    :Types:
        - `affiliation`: `str`
        - `role`: `str`
        - `jid`: `JID`
        - `nick`: `unicode`
        - `actor`: `JID`
        - `reason`: `unicode`
    """
    def __init__(self,node_or_affiliation,role=None,jid=None,nick=None,actor=None,reason=None):
        """
        Initialize a `MucItem` object.

        :Parameters:
            - `node_or_affiliation`: XML node to be pased or the affiliation of
              the user being described.
            - `role`: role of the user.
            - `jid`: JID of the user.
            - `nick`: nickname of the user.
            - `actor`: actor modyfying the user data.
            - `reason`: reason of change of the user data.
        :Types:
            - `node_or_affiliation`: `libxml2.xmlNode` or `str`
            - `role`: `str`
            - `jid`: `JID`
            - `nick`: `unicode`
            - `actor`: `JID`
            - `reason`: `unicode`
        """
        self.jid,self.nick,self.actor,self.affiliation,self.reason,self.role=(None,)*6
        MucItemBase.__init__(self)
        if isinstance(node_or_affiliation,libxml2.xmlNode):
            self.__from_node(node_or_affiliation)
        else:
            self.__init(node_or_affiliation,role,jid,nick,actor,reason)

    def __init(self,affiliation,role,jid=None,nick=None,actor=None,reason=None):
        """Initialize a `MucItem` object from a set of attributes.
        
        :Parameters:
            - `affiliation`: affiliation of the user.
            - `role`: role of the user.
            - `jid`: JID of the user.
            - `nick`: nickname of the user.
            - `actor`: actor modyfying the user data.
            - `reason`: reason of change of the user data.
        :Types:
            - `affiliation`: `str`
            - `role`: `str`
            - `jid`: `JID`
            - `nick`: `unicode`
            - `actor`: `JID`
            - `reason`: `unicode`
        """
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
        """Initialize a `MucItem` object from an XML node.

        :Parameters:
            - `node`: the XML node.
        :Types:
            - `node`: `libxml2.xmlNode`
        """
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
        Create XML representation of `self`.

        :Parameters:
            - `parent`: the element to which the created node should be linked to.
        :Types:
            - `parent`: `libxml2.xmlNode`

        :return: an XML node.
        :returntype: `libxml2.xmlNode`
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

    :Ivariables:
        - `code`: staus code, as defined in JEP 45
    :Types:
        - `code`: `int`
    """
    def __init__(self,node_or_code):
        """Initialize a `MucStatus` element.

        :Parameters:
            - `node_or_code`: XML node to parse or a status code.
        :Types:
            - `node_or_code`: `libxml2.xmlNode` or `int`
        """
        self.code=None
        MucItemBase.__init__(self)
        if isinstance(node_or_code,libxml2.xmlNode):
            self.__from_node(node_or_code)
        else:
            self.__init(node_or_code)

    def __init(self,code):
        """Initialize a `MucStatus` element from a status code.

        :Parameters:
            - `code`: the status code.
        :Types:
            - `code`: `int`
        """
        code=int(code)
        if code<0 or code>999:
            raise ValueError,"Bad status code"
        self.code=code

    def __from_node(self,node):
        """Initialize a `MucStatus` element from an XML node.

        :Parameters:
            - `node`: XML node to parse.
        :Types:
            - `node`: `libxml2.xmlNode`
        """
        self.code=int(node.prop("code"))

    def as_xml(self,parent):
        """
        Create XML representation of `self`.

        :Parameters:
            - `parent`: the element to which the created node should be linked to.
        :Types:
            - `parent`: `libxml2.xmlNode`

        :return: an XML node.
        :returntype: `libxml2.xmlNode`
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
    :Types:
        - `node`: `libxml2.xmlNode`
    """
    ns=MUC_USER_NS
    def get_items(self):
        """Get a list of objects describing the content of `self`.

        :return: the list of objects.
        :returntype: `list` of `MucItemBase` (`MucItem` and/or `MucStatus`)
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
        """Add an item to `self`.
        
        :Parameters:
            - `item`: the item to add.
        :Types:
            - `item`: `MucItemBase`
        """
        if not isinstance(item,MucItemBase):
            raise TypeError,"Bad item type for muc#user"
        item.as_xml(self.node)

class MucOwnerX(MucXBase):
    """
    Wrapper for http://www.jabber.org/protocol/muc#owner namespaced
    stanza payload "x" elements and usually containing information
    about a room user.

    :Ivariables:
        - `node`: wrapped XML node.
    :Types:
        - `node`: `libxml2.xmlNode`
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
        """Initialize a `MucStanzaExt` derived object."""
        if self.__class__ is MucStanzaExt:
            raise RuntimeError,"Abstract class called"
        self.node=None
        self.muc_child=None

    def get_muc_child(self):
        """
        Get the MUC specific payload element.

        :return: the object describing the stanza payload in MUC namespace.
        :returntype: `MucX` or `MucUserX` or `MucAdminQuery` or `MucOwnerX`
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

        :return: the element created.
        :returntype: `MucUserX`
        """
        self.clear_muc_child()
        self.muc_child=MucUserX(parent=self.node)
        return self.muc_child

    def make_muc_admin_quey(self):
        """
        Create <query xmlns="...muc#admin"/> element in the stanza.

        :return: the element created.
        :returntype: `MucAdminQuery`
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
        """Initialize a `MucPresence` object.

        :Parameters:
            - `node`: XML node to_jid be wrapped into the `MucPresence` object
              or other Presence object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `from_jid`: sender JID.
            - `to_jid`: recipient JID.
            - `stanza_type`: staza type: one of: None, "available", "unavailable",
              "subscribe", "subscribed", "unsubscribe", "unsubscribed" or
              "error". "available" is automaticaly changed to_jid None.
            - `stanza_id`: stanza id -- value of stanza's "id" attribute
            - `show`: "show" field of presence stanza. One of: None, "away",
              "xa", "dnd", "chat".
            - `status`: descriptive text for the presence stanza.
            - `priority`: presence priority.
            - `error_cond`: error condition name. Ignored if `stanza_type` is not "error"
        :Types:
            - `node`: `unicode` or `libxml2.xmlNode` or `pyxmpp.stanza.Stanza`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `show`: `unicode`
            - `status`: `unicode`
            - `priority`: `unicode`
            - `error_cond`: `unicode`"""
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
        """If `self` is a MUC room join request return the information contained.

        :return: the join request details or `None`.
        :returntype: `MucX`
        """
        x=self.get_muc_child()
        if not x:
            return None
        if not isinstance(x,MucX):
            return None
        return x

    def free(self):
        """Free the data associated with this `MucPresence` object."""
        self.muc_free()
        Presence.free(self)

class MucIq(Iq,MucStanzaExt):
    """
    Extend `Iq` with MUC related interface.
    """
    def __init__(self,node=None,from_jid=None,to_jid=None,stanza_type=None,stanza_id=None,
            error=None,error_cond=None):
        """Initialize an `Iq` object.

        :Parameters:
            - `node`: XML node to_jid be wrapped into the `Iq` object
              or other Iq object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `from_jid`: sender JID.
            - `to_jid`: recipient JID.
            - `stanza_type`: staza type: one of: "get", "set", "result" or "error".
            - `stanza_id`: stanza id -- value of stanza's "id" attribute. If not
              given, then unique for the session value is generated.
            - `error_cond`: error condition name. Ignored if `stanza_type` is not "error".
        :Types:
            - `node`: `unicode` or `libxml2.xmlNode` or `Iq`
            - `from_jid`: `JID`
            - `to_jid`: `JID`
            - `stanza_type`: `unicode`
            - `stanza_id`: `unicode`
            - `error_cond`: `unicode`"""
        MucStanzaExt.__init__(self)
        Iq.__init__(self,node,from_jid=from_jid,to_jid=to_jid,
                stanza_type=stanza_type,stanza_id=stanza_id,
                error=error,error_cond=error_cond)

    def copy(self):
        """ Return a copy of `self`.  """
        return MucIq(self)

    def make_kick_request(self,nick,reason):
        """
        Make the iq stanza a MUC room participant kick request.

        :Parameters:
            - `nick`: nickname of user to kick.
            - `reason`: reason of the kick.
        :Types:
            - `nick`: `unicode`
            - `reason`: `unicode`

        :return: object describing the kick request details.
        :returntype: `MucItem`
        """
        self.clear_muc_child()
        self.muc_child=MucAdminQuery(parent=self.node)
        item=MucItem("none","none",nick=nick,reason=reason)
        self.muc_child.add_item(item)
        return self.muc_child

    def free(self):
        """Free the data associated with this `MucIq` object."""
        self.muc_free()
        Iq.free(self)

# vi: sts=4 et sw=4
