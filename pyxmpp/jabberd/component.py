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

__revision__="$Id: component.py,v 1.8 2004/09/10 14:01:10 jajcus Exp $"
__docformat__="restructuredtext en"

import libxml2
import sys
import threading
import traceback
import logging

from pyxmpp.jabberd.componentstream import ComponentStream
from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.jabber import DiscoItems,DiscoInfo,DiscoIdentity
from pyxmpp.stanza import Stanza

class ComponentError(StandardError):
    pass

class FatalComponentError(ComponentError):
    pass

class Component:
    def __init__(self,jid=None,secret=None,server=None,port=5347,
            category="x-service",type="x-unknown",keepalive=0):
        self.jid=jid
        self.secret=secret
        self.server=server
        self.port=port
        self.keepalive=keepalive
        self.stream=None
        self.lock=threading.RLock()
        self.state_changed=threading.Condition(self.lock)
        self.stream_class=ComponentStream
        self.disco_items=None
        self.disco_info=None
        self.category=category
        self.type=type
        self.__logger=logging.getLogger("pyxmpp.jabberd.Component")

# public methods

    def connect(self):
        if not self.jid or self.jid.node or self.jid.resource:
            raise ClientError,"Cannot connect: no or bad JID given"
        if not self.secret:
            raise ClientError,"Cannot connect: no secret given"
        if not self.server:
            raise ClientError,"Cannot connect: no server given"
        if not self.port:
            raise ClientError,"Cannot connect: no port given"

        self.lock.acquire()
        try:
            stream=self.stream
            self.stream=None
            if stream:
                stream.close()

            self.__logger.debug("Creating component stream: %r" % (self.stream_class,))
            stream=self.stream_class(jid=self.jid,
                    secret=self.secret,
                    server=self.server,
                    port=self.port,
                    keepalive=self.keepalive)
            stream.process_stream_error=self.stream_error
            self.stream_created(stream)
            stream.state_change=self.__stream_state_change
            stream.connect()
            self.stream=stream
            self.state_changed.notify()
            self.state_changed.release()
        except:
            self.stream=None
            self.state_changed.release()
            raise
        self.disco_items=DiscoItems()
        self.disco_info=DiscoInfo()
        self.disco_identity=DiscoIdentity(self.disco_info,
                            "PyXMPP based jabberd component",
                            self.category,self.type)

    def get_stream(self):
        self.lock.acquire()
        stream=self.stream
        self.lock.release()
        return stream

    def disconnect(self):
        stream=self.get_stream()
        if stream:
            stream.disconnect()

    def socket(self):
        return self.stream.socket

    def loop(self,timeout=1):
        self.stream.loop(timeout)


# private methods
    def __stream_state_change(self,state,arg):
        self.stream_state_changed(state,arg)
        if state=="fully connected":
            self.connected()
        elif state=="authenticated":
            self.authenticated()
        elif state=="authorized":
            self.authorized()
        elif state=="disconnected":
            self.state_changed.acquire()
            try:
                if self.stream:
                    self.stream.close()
                self.stream_closed(self.stream)
                self.stream=None
                self.state_changed.notify()
            finally:
                self.state_changed.release()
            self.disconnected()

    def __disco_info(self,iq):
        q=iq.get_query()
        if q.hasProp("node"):
            node=from_utf8(q.prop("node"))
        else:
            node=None
        info=self.disco_get_info(node,iq)
        if isinstance(info,DiscoInfo):
            resp=iq.make_result_response()
            self.__logger.debug("Disco-info query: %s preparing response: %s with reply: %s"
                % (iq.serialize(),resp.serialize(),info.xmlnode.serialize()))
            resp.set_content(info.xmlnode.copyNode(1))
        elif isinstance(info,Stanza):
            resp=info
        else:
            resp=iq.make_error_response("item-not-found")
        self.__logger.debug("Disco-info response: %s" % (resp.serialize(),))
        self.stream.send(resp)

    def __disco_items(self,iq):
        q=iq.get_query()
        if q.hasProp("node"):
            node=from_utf8(q.prop("node"))
        else:
            node=None
        items=self.disco_get_items(node,iq)
        if isinstance(items,DiscoItems):
            resp=iq.make_result_response()
            self.__logger.debug("Disco-items query: %s preparing response: %s with reply: %s"
                % (iq.serialize(),resp.serialize(),items.xmlnode.serialize()))
            resp.set_content(items.xmlnode.copyNode(1))
        elif isinstance(items,Stanza):
            resp=items
        else:
            resp=iq.make_error_response("item-not-found")
        self.__logger.debug("Disco-items response: %s" % (resp.serialize(),))
        self.stream.send(resp)

# Method to override
    def idle(self):
        stream=self.get_stream()
        if stream:
            stream.idle()

    def stream_created(self,stream):
        pass

    def stream_closed(self,stream):
        pass

    def stream_error(self,err):
        self.__logger.debug("Stream error: condition: %s %r"
                % (err.get_condition().name,err.serialize()))

    def stream_state_changed(self,state,arg):
        pass

    def connected(self):
        pass

    def authenticated(self):
        self.__logger.debug("Setting up Disco handlers...")
        self.stream.set_iq_get_handler("query","http://jabber.org/protocol/disco#items",
                                    self.__disco_items)
        self.stream.set_iq_get_handler("query","http://jabber.org/protocol/disco#info",
                                    self.__disco_info)

    def authorized(self):
        pass

    def disco_get_info(self,node,iq):
        to=iq.get_to()
        if to and to!=self.jid:
            return iq.make_error_response("recipient-unavailable")
        if not node and self.disco_info:
            return self.disco_info
        return None

    def disco_get_items(self,node,iq):
        to=iq.get_to()
        if to and to!=self.jid:
            return iq.make_error_response("recipient-unavailable")
        if not node and self.disco_items:
            return self.disco_items
        return None

    def disconnected(self):
        pass

# vi: sts=4 et sw=4
