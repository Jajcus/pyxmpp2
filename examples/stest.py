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
	def post_auth(self):
		ClientStream.post_auth(self)
		if not self.version:
			self.welcome()
			return
		self.set_iq_set_handler("session","urn:ietf:params:xml:ns:xmpp-session",
								self.set_session)
	
	def set_session(self):
		iq=stanza.make_result_reply()
		self.send(iq)
		self.welcome()

	def welcome(self):
		self.disconnect_time=time.time()+60
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
