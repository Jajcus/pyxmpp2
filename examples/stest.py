#!/usr/bin/python -u

import libxml2
import time
import sys
import traceback
import socket

from pyxmpp import ClientStream,JID,Iq,Presence,Message,StreamError

class Disconnected(Exception):
	pass

class Stream(ClientStream):
	def post_auth(self):
		print ":-)"
		self.set_message_handler("normal",self.message_in)
		self.set_message_handler("chat",self.message_in)
		
	def post_disconnect(self):
		raise Disconnected
	
	def get_password(self,username,realm=None,acceptable_formats=("plain",)):
		if "plain" in acceptable_formats:
			if username==u"test":
				return "123","plain"
			elif username==unicode("¿ó³tek","iso-8859-2"):
				return unicode("zieleñ","iso-8859-2"),"plain"
		return None,None

	def message_in(self,stanza):
		echo=Message(fr=stanza.get_to(),to=stanza.get_from(),
				body=stanza.get_body(), subject=stanza.get_subject())
		self.send(echo)


libxml2.debugMemory(1)

print "creating socket..."
sock=socket.socket()
sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
sock.bind(("127.0.0.1",5222))
sock.listen(1)

print "creating stream..."
s=Stream(JID("localhost"),auth_methods=("plain","digest"))

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
	except KeyboardInterrupt:
		traceback.print_exc(file=sys.stderr)
		break
	except (StreamError,Disconnected),e:
		traceback.print_exc(file=sys.stderr)

libxml2.cleanupParser()
if libxml2.debugMemory(1) == 0:
    print "OK"
else:
    print "Memory leak %d bytes" % (libxml2.debugMemory(1))
    libxml2.dumpMemory()
