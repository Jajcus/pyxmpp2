#!/usr/bin/python -u
# -*- coding: utf-8 -*-

import libxml2
import time
import traceback
import sys
import logging

from pyxmpp.all import JID,Iq,Presence,Message,StreamError
from pyxmpp.jabber.all import Client

class Disconnected(Exception):
    pass

class MyClient(Client):
    def session_started(self):
        self.stream.send(Presence())

    def idle(self):
        print "idle"
        Client.idle(self)
        if self.session_established:
            target=JID("jajcus",s.jid.domain)
            self.stream.send(Message(to_jid=target,body=unicode("Teścik","utf-8")))

    def post_disconnect(self):
        print "Disconnected"
        raise Disconnected

logger=logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

libxml2.debugMemory(1)

print "creating stream..."
s=MyClient(jid=JID("test@localhost/Test"),password=u"123",auth_methods=["sasl:DIGEST-MD5","digest"])

print "connecting..."
s.connect()

print "processing..."
try:
    try:
        s.loop(1)
    finally:
        s.disconnect()
except KeyboardInterrupt:
    traceback.print_exc(file=sys.stderr)
except (StreamError,Disconnected),e:
    raise

libxml2.cleanupParser()
if libxml2.debugMemory(1) == 0:
    print "OK"
else:
    print "Memory leak %d bytes" % (libxml2.debugMemory(1))
    libxml2.dumpMemory()
# vi: sts=4 et sw=4
