#!/usr/bin/python -u

import libxml2
import time
import sys
import traceback
import socket
import logging

from pyxmpp.all import JID,Iq,Presence,Message,StreamError
from pyxmpp.jabber.all import LegacyClientStream

accounts={
        u'test': '123',
    };

class Stream(LegacyClientStream):
    def state_change(self,state,arg):
        print "*** State changed: %s %r ***" % (state,arg)
        if state=="authorized":
            self.disconnect_time=time.time()+60
            if not self.version:
                self.welcome()
                return
            self.set_iq_set_handler("session","urn:ietf:params:xml:ns:xmpp-session",
                                    self.set_session)

    def set_session(self,stanza):
        fr=stanza.get_from()
        if fr and fr!=self.peer:
            iq=stanza.make_error_response("forbidden")
            self.send(iq)
        else:
            iq=stanza.make_result_response()
            iq.set_to(None)
            self.send(iq)
            self.welcome()
        iq.free()

    def welcome(self):
        m=Message(type="chat",to=self.peer,
                body="You have authenticated with: %r" % (self.auth_method_used))
        self.send(m)
        m=Message(type="chat",to=self.peer,body="You will be disconnected in 1 minute.")
        self.send(m)
        m=Message(type="chat",to=self.peer,body="Thank you for testing.")
        self.send(m)
        self.set_message_handler('chat',self.echo_message)
        self.set_message_handler('normal',self.echo_message)

    def echo_message(self,message):
        typ=message.get_type()
        body=message.get_body()
        if not body:
            return
        body=u"ECHO: %s" % (body,)
        subject=message.get_subject()
        if subject:
            subject=u"Re: %s" % (subject,)
        m=Message(type=typ,to=self.peer,body=body,subject=subject)
        self.send(m)

    def idle(self):
        ClientStream.idle(self)
        if not self.peer_authenticated:
            return
        if time.time()>=self.disconnect_time:
            m=Message(type="chat",to=self.peer,body="Bye.")
            self.send(m)
            self.disconnect()

#   def get_realms(self):
#       return None

    def get_password(self,username,realm=None,acceptable_formats=("plain",)):
        if "plain" in acceptable_formats and accounts.has_key(username):
            return accounts[username],"plain"
        return None,None

logger=logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

print "creating socket..."
sock=socket.socket()
sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
sock.bind(("127.0.0.1",5222))
sock.listen(1)

print "creating stream..."
s=Stream(JID("localhost"),auth_methods=("sasl:DIGEST-MD5","plain","digest"))

while 1:
    print "accepting..."
    s.accept(sock)

    print "processing..."
    try:
        try:
            s.loop(1)
        finally:
            print "closing..."
            s.close()
    except StreamError:
        traceback.print_exc(file=sys.stderr)
        continue
# vi: sts=4 et sw=4
