#!/usr/bin/python -u

import libxml2
import time
import sys
import traceback
import socket

from pyxmpp import ClientStream,JID,Iq,Presence,Message,StreamError

accounts={
		u'test': '123',
		u'kurczê': '¿ó³tko',
	};

class Stream(ClientStream):
	def __init__(self,jid,password=None,server=None,port=5222,
			auth_methods=["sasl:DIGEST-MD5","digest"],
			enable_tls=0,require_tls=0):
		ClientStream.__init__(self,jid,password,server,port,auth_methods,
								enable_tls,require_tls)
		self.disconnect_time=time.time()+60

	def post_auth(self):
		m=Message(type="chat",to=self.peer,
				body="You have authenticated with: %r" % (self.auth_method_used))
		self.send(m)
		m=Message(type="chat",to=self.peer,body="You will be disconnected in 1 minute.")
		self.send(m)
		m=Message(type="chat",to=self.peer,body="Thank you for testing.")
		self.send(m)

	def idle(self):
		ClientStream.idle(self)
		if time.time()>=self.disconnect_time:
			m=Message(type="chat",to=self.peer,
					body="Bye." % (self.auth_method_used))
			self.send(m)
			self.disconnect()
		
	def get_password(self,username,realm=None,acceptable_formats=("plain",)):
		if "plain" in acceptable_formats and accounts.has_key(username):
			return accounts[username],"plain"
		return None,None

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
		s.loop(1)
	finally:
		print "closing..."
		s.close()
				
		
	def get_password(self,username,realm=None,acceptable_formats=("plain",)):
		if "plain" in acceptable_formats:
			if username==u"test":
				return "123","plain"
			elif username==unicode("¿ó³tek","iso-8859-2"):
				return unicode("zieleñ","iso-8859-2"),"plain"
		return None,None

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
		s.loop(1)
	finally:
		print "closing..."
		s.close()
