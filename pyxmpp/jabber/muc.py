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

__revision__="$Id: muc.py,v 1.24 2004/09/14 19:58:05 jajcus Exp $"
__docformat__="restructuredtext en"

import libxml2
import logging
from types import StringType,UnicodeType

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.stanza import common_doc,common_root
from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.iq import Iq
from pyxmpp.jid import JID
from pyxmpp import xmlextra

import weakref

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
        MucXBase.__init__(self,node=None,copy=copy,parent=parent)
    # FIXME: set/get password/history

class MucItemBase:
    """
    Base class for <status/> and <item/> element wrappers.
    """
    def __init__(self):
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
        item.as_xml(self.node)

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
        if not hasattr(self,"node"):
            raise RuntimeError,"Abstract class called"
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
    def __init__(self,node=None,**kw):
        """
        Initialize `self` from an XML node or a set of attributes.

        See `Presence.__init__` for allowed keyword arguments.
        """
        self.node=None
        MucStanzaExt.__init__(self)
        apply(Presence.__init__,[self,node],kw)

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
    def __init__(self,node=None,**kw):
        """
        Initialize `self` from an XML node or a set of attributes.

        See `Presence.__init__` for allowed keyword arguments.
        """
        self.node=None
        MucStanzaExt.__init__(self)
        apply(Iq.__init__,[self,node],kw)

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

class MucRoomHandler:
    """
    Base class for MUC room handlers.

    Methods of this class will be called for various events in the room.

    :Ivariables:
      - `room_state`: MucRoomState object describing room state and its
        participants.

    """
    def __init__(self):
        self.room_state=None
        self.__logger=logging.getLogger("pyxmpp.jabber.MucRoomHandler")

    def assign_state(self,state_obj):
        """Called to assign a `MucRoomState` object to this `MucRoomHandler` instance."""
        self.room_state=state_obj

    def user_joined(self,user,stanza):
        """
        Called when a new participant joins the room.

        :Parameters:
            - `user`: the user joining.
            - `stanza`: the stanza received.
        
        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def user_left(self,user,stanza):
        """
        Called when a participant leaves the room.

        :Parameters:
            - `user`: the user leaving.
            - `stanza`: the stanza received.
        
        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def role_changed(self,user,old_role,new_role,stanza):
        """
        Called when a role of an user has been changed.

        :Parameters:
            - `user`: the user (after update).
            - `old_role`: user's role before update.
            - `new_role`: user's role after update.
            - `stanza`: the stanza received.
        
        :Types:
            - `user`: `MucRoomUser`
            - `old_role`: `unicode`
            - `new_role`: `unicode`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def affiliation_changed(self,user,old_aff,new_aff,stanza):
        """
        Called when a affiliation of an user has been changed.

        `user` MucRoomUser object describing the user (after update).
        `old_aff` is user's affiliation before update.
        `new_aff` is user's affiliation after update.
        `stanza` the stanza received.
        """
        pass

    def nick_change(self,user,new_nick,stanza):
        """
        Called when user nick change is started.

        :Parameters:
            - `user`: the user (before update).
            - `new_nick`: the new nick.
            - `stanza`: the stanza received.

        :Types:
            - `user`: `MucRoomUser`
            - `new_nick`: `unicode`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def nick_changed(self,user,old_nick,stanza):
        """
        Called after a user nick has been changed.

        :Parameters:
            - `user`: the user (after update).
            - `old_nick`: the old nick.
            - `stanza`: the stanza received.
        
        :Types:
            - `user`: `MucRoomUser`
            - `old_nick`: `unicode`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def presence_changed(self,user,stanza):
        """
        Called whenever user's presence changes (includes nick, role or
        affiliation changes).

        :Parameters:
            - `user`: MucRoomUser object describing the user.
            - `stanza`: the stanza received.
            
        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def subject_changed(self,user,stanza):
        """
        Called when the room subject has been changed.

        :Parameters:
            - `user`: the user changing the subject.
            - `stanza`: the stanza used to change the subject.
            
        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def message_received(self,user,stanza):
        """
        Called when groupchat message has been received.

        :Parameters:
            - `user`: the sender.
            - `stanza`: is the message stanza received.
            
        :Types:
            - `user`: `MucRoomUser`
            - `stanza`: `pyxmpp.stanza.Stanza`
        """
        pass

    def error(self,stanza):
        err=stanza.get_error()
        self.__logger.debug("Error from: %r Condition: %r"
                % (stanza.get_from(),err.get_condition))

class MucRoomUser:
    """
    Describes a user of a MUC room.

    Public attributes (should not be changed):
    presence - last presence stanza received for the user
    role - user's role
    affiliation - user's affiliation
    room_jid - user's room jid
    real_jid - user's real jid or None if not available
    nick - user's nick (resource part of room_jid)
    """
    def __init__(self,presence_or_user_or_jid):
        """
        Initialize `self` from presence stanza or a JID.

        When `presence_or_user_or_jid` is a JID user's
        role and affiliation are set to "none".
        """
        if isinstance(presence_or_user_or_jid,MucRoomUser):
            self.presence=presence_or_user_or_jid.presence
            self.role=presence_or_user_or_jid.role
            self.affiliation=presence_or_user_or_jid.affiliation
            self.room_jid=presence_or_user_or_jid.room_jid
            self.real_jid=presence_or_user_or_jid.real_jid
            self.nick=presence_or_user_or_jid.nick
            self.new_nick=None
        else:
            self.affiliation="none"
            self.presence=None
            self.real_jid=None
            self.new_nick=None
            if isinstance(presence_or_user_or_jid,JID):
                self.nick=presence_or_user_or_jid.resource
                self.room_jid=presence_or_user_or_jid
                self.role="none"
            elif isinstance(presence_or_user_or_jid,Presence):
                self.nick=None
                self.room_jid=None
                self.role="participant"
                self.update_presence(presence_or_user_or_jid)
            else:
                raise TypeError,"Bad argument type for MucRoomUser constructor"

    def update_presence(self,presence):
        """
        Update user information using the presence stanza provided.
        """
        self.presence=MucPresence(presence)
        t=presence.get_type()
        if t=="unavailable":
            self.role="none"
            self.affiliation="none"
        self.room_jid=self.presence.get_from()
        self.nick=self.room_jid.resource
        mc=self.presence.get_muc_child()
        if isinstance(mc,MucUserX):
            items=mc.get_items()
            for item in items:
                if not isinstance(item,MucItem):
                    continue
                if item.role:
                    self.role=item.role
                if item.affiliation:
                    self.affiliation=item.affiliation
                if item.jid:
                    self.real_jid=item.jid
                if item.nick:
                    self.new_nick=item.nick
                break
    def same_as(self,other):
        return self.room_jid==other.room_jid

class MucRoomState:
    """
    Describes the state of a MUC room, handles room events
    and provides an interface for room actions.

    :Ivariables:
        - `own_jid`: real jid of the owner (client using this class).
        - `room_jid`: room jid of the owner.
        - `handler`: MucRoomHandler object containing callbacks to be called.
        - `manager`: MucRoomManager object managing this room.
        - `joined`: True if the channel is joined.
        - `subject`: current subject of the room.
        - `users`: dictionary of users in the room. Nicknames are the keys.
        - `me`: MucRoomUser instance of the owner.
    """
    def __init__(self,manager,own_jid,room_jid,handler):
        """
        Initialize `self` with given attributes.
        """
        self.own_jid=own_jid
        self.room_jid=room_jid
        self.handler=handler
        self.manager=weakref.proxy(manager)
        self.joined=False
        self.subject=None
        self.users={}
        self.me=MucRoomUser(room_jid)
        handler.assign_state(self)
        self.__logger=logging.getLogger("pyxmpp.jabber.MucRoomState")

    def get_user(self,nick_or_jid,create=False):
        """
        Return room user with given nick or JID.

        If JID is given with non-empty resource and user is not known, then
        create a new MucRoomUser object. Otherwise return None if the user is
        not known.
        """
        if isinstance(nick_or_jid,JID):
            if not nick_or_jid.resource:
                return None
            for u in self.users.values():
                if nick_or_jid in (u.room_jid,u.real_jid):
                    return u
            if create:
                return MucRoomUser(nick_or_jid)
            else:
                return None
        return self.users.get(nick_or_jid)

    def set_stream(self,stream):
        """
        Mark the room not joined and inform `self.handler` that it was left.

        Called when current stream changes.
        """
        if self.joined and self.handler:
            self.handler.user_left(self.me,None)
        self.joined=False

    def join(self):
        """
        Send a join request for the room.
        """
        if self.joined:
            raise RuntimeError,"Room is already joined"
        p=MucPresence(to=self.room_jid)
        p.make_join_request()
        self.manager.stream.send(p)

    def leave(self):
        """
        Send a leave request for the room.
        """
        p=MucPresence(to=self.room_jid,typ="unavailable")
        self.manager.stream.send(p)

    def send_message(self,body):
        """
        Send a message to the room.
        """
        m=Message(to=self.room_jid.bare(),typ="groupchat",body=body)
        self.manager.stream.send(m)

    def set_subject(self,subject):
        """
        Send a subject change request to the room.
        """
        m=Message(to=self.room_jid.bare(),typ="groupchat",subject=subject)
        self.manager.stream.send(m)

    def change_nick(self,new_nick):
        """
        Send a nick change request to the room.
        """
        new_room_jid=JID(self.room_jid.node,self.room_jid.domain,new_nick)
        p=Presence(to=new_room_jid)
        self.manager.stream.send(p)

    def get_room_jid(self,nick=None):
        """
        Return the room jid or a room jid for given `nick`.
        """
        if nick is None:
            return self.room_jid
        return JID(self.room_jid.node,self.room_jid.domain,nick)

    def get_nick(self):
        """
        Return own nick.
        """
        return self.room_jid.resource

    def process_available_presence(self,stanza):
        """
        Process <presence/> received from the room.
        """
        fr=stanza.get_from()
        if not fr.resource:
            return
        nick=fr.resource
        user=self.users.get(nick)
        if user:
            old_user=MucRoomUser(user)
            user.update_presence(stanza)
            user.nick=nick
        else:
            old_user=None
            user=MucRoomUser(stanza)
            self.users[user.nick]=user
        self.handler.presence_changed(user,stanza)
        if fr==self.room_jid and not self.joined:
            self.joined=True
            self.me=user
        if not old_user or old_user.role=="none":
            self.handler.user_joined(user,stanza)
        else:
            if old_user.nick!=user.nick:
                self.handler.nick_changed(user,old_user.nick,stanza)
                if old_user.room_jid==self.room_jid:
                    self.room_jid=fr
            if old_user.role!=user.role:
                self.handler.role_changed(user,old_user.role,user.role,stanza)
            if old_user.affiliation!=user.affiliation:
                self.handler.affiliation_changed(user,old_user.affiliation,user.affiliation,stanza)

    def process_unavailable_presence(self,stanza):
        """
        Process <presence type="unavailable"/> received from the room.
        """
        fr=stanza.get_from()
        if not fr.resource:
            return
        nick=fr.resource
        user=self.users.get(nick)
        if user:
            old_user=MucRoomUser(user)
            user.update_presence(stanza)
            self.handler.presence_changed(user,stanza)
            if user.new_nick:
                mc=stanza.get_muc_child()
                if isinstance(mc,MucUserX):
                    renames=[i for i in mc.get_items() if isinstance(i,MucStatus) and i.code==303]
                    if renames:
                        self.users[user.new_nick]=user
                        del self.users[nick]
                        return
        else:
            old_user=None
            user=MucRoomUser(stanza)
            self.users[user.nick]=user
            self.handler.presence_changed(user,stanza)
        if fr==self.room_jid and self.joined:
            self.joined=False
            self.handler.user_left(user,stanza)
            self.manager.forget(self)
            self.me=user
        elif old_user:
            self.handler.user_left(user,stanza)
        # TODO: kicks

    def process_groupchat_message(self,stanza):
        """
        Process <message type="groupchat"/> received from the room.
        """
        fr=stanza.get_from()
        user=self.get_user(fr,True)
        s=stanza.get_subject()
        if s:
            self.subject=s
            self.handler.subject_changed(user,stanza)
        else:
            self.handler.message_received(user,stanza)

    def process_error_message(self,stanza):
        """
        Process <message type="error"/> received from the room.
        """
        self.handler.error(stanza)

    def process_error_presence(self,stanza):
        """
        Process <presence type="error"/> received from the room.
        """
        self.handler.error(stanza)

class MucRoomManager:
    """
    Manage collection of MucRoomState objects and dispatch events.

    :Ivariables:
      - `rooms`: a dictionary containing known MUC rooms. Unicode room JIDs are the
        keys.
    
    """
    def __init__(self,stream):
        """
        Initialize `self` and assign it the given `stream`.
        """
        self.rooms={}
        self.set_stream(stream)
        self.__logger=logging.getLogger("pyxmpp.jabber.MucRoomManager")

    def set_stream(self,stream):
        """
        Change the stream assigned to `self`.
        """
        self.jid=stream.me
        self.stream=stream
        for r in self.rooms.values():
            r.set_stream(stream)

    def set_handlers(self,priority=10):
        """
        Assign stanza handlers in `self` to the `self.stream`.
        """
        self.stream.set_message_handler("groupchat",self.__groupchat_message,None,priority)
        self.stream.set_message_handler("error",self.__error_message,None,priority)
        self.stream.set_presence_handler("available",self.__presence_available,None,priority)
        self.stream.set_presence_handler("unavailable",self.__presence_unavailable,None,priority)
        self.stream.set_presence_handler("error",self.__presence_error,None,priority)

    def join(self,room,nick,handler):
        """
        Create and return a new RoomState object and request joining
        to a MUC room.

        `room` is the name of a room to be joined
        `nick` is the nickname to be used in the room
        `handler` is a MucRoomHandler object which will handle room events
        """
        if not room.node or room.resource:
            raise ValueError,"Invalid room JID"
        rs=MucRoomState(self,self.stream.me,
                JID(room.node,room.domain,nick),handler)
        self.rooms[rs.room_jid.bare().as_unicode()]=rs
        rs.join()
        return rs

    def get_room_state(self,room):
        return self.rooms.get(room.bare().as_unicode())

    def forget(self,rs):
        """
        Remove a RoomStateObject `rs` from `self.rooms`.
        """
        try:
            del self.rooms[rs.room_jid.bare().as_unicode()]
        except KeyError:
            pass

    def __groupchat_message(self,stanza):
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            self.__logger.debug("groupchat message from unknown source")
            return False
        rs.process_groupchat_message(stanza)
        return True

    def __error_message(self,stanza):
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            return False
        rs.process_error_message(stanza)
        return True

    def __presence_error(self,stanza):
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            return False
        rs.process_error_presence(stanza)
        return True

    def __presence_available(self,stanza):
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            return False
        rs.process_available_presence(MucPresence(stanza))
        return True

    def __presence_unavailable(self,stanza):
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            return False
        rs.process_unavailable_presence(MucPresence(stanza))
        return True

# vi: sts=4 et sw=4
