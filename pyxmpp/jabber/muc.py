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

import logging

from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.jid import JID

from pyxmpp.jabber.muccore import MucPresence,MucUserX,MucItem,MucStatus

import weakref

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
        p=MucPresence(to_jid=self.room_jid)
        p.make_join_request()
        self.manager.stream.send(p)

    def leave(self):
        """
        Send a leave request for the room.
        """
        p=MucPresence(to_jid=self.room_jid,stanza_type="unavailable")
        self.manager.stream.send(p)

    def send_message(self,body):
        """
        Send a message to the room.
        """
        m=Message(to_jid=self.room_jid.bare(),stanza_type="groupchat",body=body)
        self.manager.stream.send(m)

    def set_subject(self,subject):
        """
        Send a subject change request to the room.
        """
        m=Message(to_jid=self.room_jid.bare(),stanza_type="groupchat",subject=subject)
        self.manager.stream.send(m)

    def change_nick(self,new_nick):
        """
        Send a nick change request to the room.
        """
        new_room_jid=JID(self.room_jid.node,self.room_jid.domain,new_nick)
        p=Presence(to_jid=new_room_jid)
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
        self.stream,self.jid=(None,)*2
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
