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
    """
    Wrapper for http://www.jabber.org/protocol/muc#user namespaced 
    stanza payload "x" elements.
    """
    ns=MUC_USER_NS
    def __init__(self,node=None,copy=True,parent=None):
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

class MucRoomHandler:
    """
    Base class for MUC room handlers.
    
    Methods of this class will be called for various events in the room.
    """
    def __init__(self):
        self.room_state=None
        
    def assign_state(self,state_obj):
        """Called to assign a `MucRoomState` object to this `MucRoomHandler` instance."""
        self.room_state=state_obj
        
    def joined(self,user):
        """Called after joining the room."""
        pass

    def left(self,user):
        """
        Called after leaving the room.
        
        `user` MucRoomUser object describing the event.
        """
        pass

    def other_joined(self,user):
        """
        Called when a new participant joins the room.
        """
        pass
    def other_left(self,user):
        """
        Called when a new participant leaves the room.
        """
        pass
    def role_changed(self,user,old_role,new_role):
        """
        Called when the role has been changed.
        """
        pass
    def other_role_changed(self,user,old_role,new_role):
        """
        Called when other participant's role has been changed.
        """
        pass
    def affiliation_changed(self,user,old_aff,new_aff):
        """
        Called when the affiliation has been changed.
        """
        pass
    def other_affiliation_changed(self,user,old_aff,new_aff):
        """
        Called when other participant's affiliation has been changed.
        
        `old_item` is MucItem object describing user's previous affiliation.
        `new_item` is MucItem object describing the event and user's new affiliation.
        """
        pass
    def subject_changed(self,nick,stanza):
        """
        Called when the room subject has been changed.

        `nick` is a nick of the user changing subject.
        `stanza` is the stanza used to change the subject.
        """
        pass
    def message_received(self,nick,stanza):
        """
        Called when groupchat message has been received.

        `nick` is a nick of the sender.
        `stanza` is the message stanza received.
        """
        pass
    def error(self,stanza):
        err=stanza.get_error()
        self.debug("Error from: %r Condition: %r" 
                % (stanza.get_from(),err.get_condition)) 
    def debug(self,s):
        self.room_state.stream.debug(s)

class MucRoomUser:
    def __init__(self,presence_or_user):
        if isinstance(presence_or_user,MucRoomUser):
            self.presence=presence_or_user.presence
            self.role=presence_or_user.role
            self.affiliation=presence_or_user.affiliation
            self.room_jid=presence_or_user.room_jid
            self.real_jid=presence_or_user.real_jid
            self.nick=presence_or_user.nick
        else:
            self.presence=None
            self.role="participant"
            self.affiliation="none"
            self.room_jid=None
            self.real_jid=None
            self.nick=None
            self.update_presence(presence_or_user)
        
    def update_presence(self,presence):
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
            if items:
                item=items[0]
                if item.role:
                    self.role=item.role
                if item.affiliation:
                    self.affiliation=item.affiliation
                if item.jid:
                    self.real_jid=item.jid
        
class MucRoomState:
    def __init__(self,manager,own_jid,room_jid,handler):
        self.own_jid=own_jid
        self.room_jid=room_jid
        self.handler=handler
        self.manager=weakref.proxy(manager)
        self.joined=False
        self.subject=None
        self.users={}
        handler.assign_state(self)

    def get_user(self,nick_or_jid):
        if isinstance(nick_or_jid,JID):
            for u in self.users.values():
                if nick_or_jid in (u.room_jid,u.real_jid):
                    return u
            return None
        return self.users.get(nick_or_jid)

    def set_stream(self,stream):
        if self.joined and self.handler:
            self.handler.left(self,None)
        self.joined=False

    def join(self):
        p=MucPresence(to=self.room_jid)
        p.make_join_request()
        self.manager.stream.send(p)
        
    def leave(self):
        p=MucPresence(to=self.room_jid,type="unavailable")
        self.manager.stream.send(p)

    def send_message(self,body):
        m=Message(to=self.room_jid.bare(),type="groupchat",body=body)
        self.manager.stream.send(m)

    def set_subject(self,subject):
        m=Message(to=self.room_jid.bare(),type="groupchat",subject=subject)
        self.manager.stream.send(m)
        
    def get_room_jid(self,nick=None):
        if nick is None:
            return self.room_jid
        return JID(self.room_jid.node,self.room_jid.domain,nick)
            
    def get_nick(self):
        return self.room_jid.resource
       
    def process_available_presence(self,stanza):
        fr=stanza.get_from()
        if not fr.resource:
            return
        nick=fr.resource
        user=self.users.get(nick)
        if user:
            old_user=MucRoomUser(user)
            user.update_presence(stanza)
        else:
            old_user=None
            user=MucRoomUser(stanza)
            self.users[user.nick]=user
        if fr==self.room_jid and not self.joined:
            self.joined=True
            self.handler.joined(user)
        elif not old_user:
            self.handler.other_joined(user)
        # TODO: role changes, affiliation changes, nick changes
        
    def process_unavailable_presence(self,stanza):
        fr=stanza.get_from()
        if not fr.resource:
            return
        nick=fr.resource
        user=self.users.get(nick)
        if user:
            old_user=MucRoomUser(stanza)
            user.update_presence(stanza)
        else:
            old_user=None
            user=MucRoomUser(stanza)
            self.users[user.nick]=user
        if fr==self.room_jid and self.joined:
            self.joined=False
            self.handler.left(user)
            self.manager.forget(self)
        elif old_user:
            self.handler.other_left(user)
        # TODO: kicks, nick changes
        
    def process_groupchat_message(self,stanza):
        s=stanza.get_subject()
        if s:
            self.subject=s
            self.handler.subject_changed(stanza.get_from().resource,stanza)
        else:
            self.handler.message_received(stanza.get_from().resource,stanza)
    
    def process_error_message(self,stanza):
        self.handler.error(stanza)

    def process_error_presence(self,stanza):
        self.handler.error(stanza)

class MucRoomManager:
    def __init__(self,stream):
        self.rooms={}
        self.set_stream(stream)
        
    def set_stream(self,stream):
        self.jid=stream.jid
        self.stream=stream
        for r in self.rooms.values():
            r.set_stream(stream)

    def set_handlers(self,priority=10):
        self.stream.set_message_handler("groupchat",self.__groupchat_message,None,priority)
        self.stream.set_message_handler("error",self.__error_message,None,priority)
        self.stream.set_presence_handler("available",self.__presence_available,None,priority)
        self.stream.set_presence_handler("unavailable",self.__presence_unavailable,None,priority)
        self.stream.set_presence_handler("error",self.__presence_error,None,priority)

    def join(self,room,nick,handler):
        if not room.node or room.resource:
            raise ValueError,"Invalid room JID"
        rs=MucRoomState(self,self.stream.jid,
                JID(room.node,room.domain,nick),handler)
        self.rooms[rs.room_jid.bare().as_unicode()]=rs
        rs.join()
        return rs

    def forget(self,rs):
        try:
            del self.rooms[rs.room_jid.bare().as_unicode()]
        except KeyError:
            pass
            
    def __groupchat_message(self,stanza):
        fr=stanza.get_from()
        key=fr.bare().as_unicode()
        rs=self.rooms.get(key)
        if not rs:
            self.debug("groupchat message from unknown source")
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
        rs.process_presence_error(stanza)
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

# vi: sts=4 et sw=4
