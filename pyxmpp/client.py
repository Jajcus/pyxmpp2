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
import sys
import threading
import traceback

from clientstream import ClientStream
from jid import JID
from iq import Iq
from presence import Presence
from utils import to_utf8,from_utf8
from roster import Roster

class ClientError(StandardError):
    pass

class FatalClientError(ClientError):
    pass

class Client:
    def __init__(self,jid=None,password=None,server=None,port=5222,
            auth_methods=["sasl:DIGEST-MD5"],
            tls_settings=None,keepalive=0):

        self.jid=jid
        self.password=password
        self.server=server
        self.port=port
        self.auth_methods=auth_methods
        self.tls_settings=tls_settings
        self.keepalive=keepalive
        self.stream=None
        self.lock=threading.RLock()
        self.state_changed=threading.Condition(self.lock)
        self.session_established=0
        self.roster=None
        self.stream_class=ClientStream

# public methods

    def connect(self,register=0):
        if not self.jid:
            raise ClientError,"Cannot connect: no or bad JID given"
        if not register and not self.password:
            raise ClientError,"Cannot connect: no password given"
        if register:
            raise ClientError,"In-band registration not implemented yet"

        self.lock.acquire()
        try:
            stream=self.stream
            self.stream=None
            if stream:
                stream.close()

            if self.server:
                server=self.server
            else:
                server=self.jid.domain

            self.debug("Creating client stream: %r, auth_methods=%r"
                    % (self.stream_class,self.auth_methods))
            stream=self.stream_class(jid=self.jid,
                    password=self.password,
                    server=server,
                    port=self.port,
                    auth_methods=self.auth_methods,
                    tls_settings=self.tls_settings,
                    keepalive=self.keepalive)
            stream.debug=self.debug
            stream.print_exception=self.print_exception
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

    def get_stream(self):
        self.lock.acquire()
        stream=self.stream
        self.lock.release()
        return stream

    def disconnect(self):
        stream=self.get_stream()
        if stream:
            stream.disconnect()

    def request_session(self):
        stream=self.get_stream()
        if not stream.version:
            self.state_changed.acquire()
            self.session_established=1
            self.state_changed.notify()
            self.state_changed.release()
            self.session_started()
        else:
            iq=Iq(type="set")
            iq.new_query("urn:ietf:params:xml:ns:xmpp-session","session")
            stream.set_response_handlers(iq,
                self.__session_result,self.__session_error,self.__session_timeout)
            stream.send(iq)

    def request_roster(self):
        stream=self.get_stream()
        iq=Iq(type="get")
        iq.new_query("jabber:iq:roster")
        stream.set_response_handlers(iq,
            self.__roster_result,self.__roster_error,self.__roster_timeout)
        stream.set_iq_set_handler("query","jabber:iq:roster",self.__roster_push)
        stream.send(iq)

    def socket(self):
        return self.stream.socket

    def loop(self,timeout=1):
        self.stream.loop(timeout)

# private methods

    def __session_timeout(self,k,v):
        raise FatalClientError("Timeout while tryin to establish a session")

    def __session_error(self,iq):
        raise FatalClientError("Failed to establish a session")

    def __session_result(self,iq):
        self.state_changed.acquire()
        self.session_established=1
        self.state_changed.notify()
        self.state_changed.release()
        self.session_started()

    def __roster_timeout(self,k,v):
        raise ClientError("Timeout while tryin to retrieve roster")

    def __roster_error(self,iq):
        raise ClientError("Roster retrieval failed")

    def __roster_result(self,iq):
        q=iq.get_query()
        if q:
            self.state_changed.acquire()
            self.roster=Roster(q)
            self.state_changed.notify()
            self.state_changed.release()
            self.roster_updated()
        else:
            raise ClientError("Roster retrieval failed")

    def __roster_push(self,iq):
        fr=iq.get_from()
        if fr and fr!=self.jid:
            resp=iq.make_error_response("forbidden")
            self.stream.send(resp)
            raise ClientError("Got roster update from wrong source")
        if not self.roster:
            raise ClientError("Roster update, but no roster")
        q=iq.get_query()
        item=self.roster.update(q)
        if item:
            self.roster_updated(item)
        resp=iq.make_result_response()
        self.stream.send(resp)

    def __stream_state_change(self,state,arg):
        self.stream_state_changed(state,arg)
        if state=="fully connected":
            self.connected()
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

# Method to override
    def idle(self):
        stream=self.get_stream()
        if stream:
            stream.idle()

    def stream_created(self,stream):
        pass

    def stream_closed(self,stream):
        pass

    def session_started(self):
        p=Presence()
        self.stream.send(p)
        self.request_roster()

    def stream_error(self,err):
        self.debug("Stream error: condition: %s %r"
                % (err.get_condition().name,err.serialize()))

    def roster_updated(self,item=None):
        pass

    def stream_state_changed(self,state,arg):
        pass

    def connected(self):
        pass

    def authenticated(self):
        pass

    def authorized(self):
        self.request_session()

    def disconnected(self):
        pass

    def debug(self,str):
        print >>sys.stderr,"DEBUG:",str

    def print_exception(self):
        for s in traceback.format_exception(sys.exc_type,sys.exc_value,sys.exc_traceback):
            if s[-1]=='\n':
                s=s[:-1]
            self.debug(s)
# vi: sts=4 et sw=4
