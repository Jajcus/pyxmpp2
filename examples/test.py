#!/usr/bin/python -u

import libxml2
import time
import traceback
import sys

from pyxmpp import ClientStream,JID,Iq,Presence,Message,StreamError

class Disconnected(Exception):
	pass

class Stream(ClientStream):
	def post_auth(self):
		print ":-)"
		self.send(Presence())
	def idle(self):
		print "idle"
		ClientStream.idle(self)
		if self.authenticated:
			target=JID("jajcus",s.jid.domain)
			self.send(Message(to=target,body=unicode("Te¶cik","iso-8859-2")))
	def post_disconnect(self):
		print "Disconnected"
		raise Disconnected

libxml2.debugMemory(1)

print "creating stream..."
#s=Stream(JID(unicode("¿ó³tek","iso-8859-2"),"localhost","Test"),unicode("zieleñ","iso-8859-2"))
s=Stream(JID("pyxmpp","jabberd.jabberstudio.org","Test"),"123",port=15222,auth_methods=["sasl:DIGEST-MD5","digest","plain"])

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
