#!/usr/bin/python -u
#
# This example is a simple "echo" component
# 
# After connecting to jabberd it will echo messages and presence. This
# component also has basic Disco support (implemented in
# pyxmpp.jabberd.Component class) and replies to version queries.
#
# To use it with jabberd 2.0 no changes in jabberd configuration are needed
# just pass jabberd 2.0 router IP, port and secret as command args
#
# For jabberd 1.4 (and similar) servers special "service" section must be added:
# eg.:
#
#  <service id="echolinker">
#    <host>echo.localhost</host>
#    <accept>
#      <ip>127.0.0.1</ip>
#      <port>5347</port>
#      <secret>verysecret</secret>
#    </accept>
#  </service>

import sys

from pyxmpp import ClientStream,JID,Iq,Presence,Message,StreamError
import pyxmpp.jabberd

class Component(pyxmpp.jabberd.Component):
	def stream_state_changed(self,state,arg):
		print "*** State changed: %s %r ***" % (state,arg)

	def authenticated(self):
		pyxmpp.jabberd.Component.authenticated(self)
		self.stream.set_iq_get_handler("query","jabber:iq:version",self.get_version)
		self.stream.set_presence_handler("available",self.presence)
		self.stream.set_presence_handler("subscribe",self.presence_control)
		self.stream.set_message_handler("normal",self.message)

	def get_version(self,iq):
		iq=iq.make_result_response()
	        q=iq.new_query("jabber:iq:version")
                q.newTextChild(q.ns(),"name","Echo component")
                q.newTextChild(q.ns(),"version","1.0")
                self.stream.send(iq)
		return 1

	def message(self,stanza):
		subject=stanza.get_subject()
		if subject:
			subject=u"Re: "+subject
		m=Message(
			to=stanza.get_from(),
			fr=stanza.get_to(),
			type=stanza.get_type(),
			subject=subject,
			body=stanza.get_body())
		self.stream.send(m)
		return 1

	def presence(self,stanza):
		p=Presence(
			type=stanza.get_type(),
			to=stanza.get_from(),
			fr=stanza.get_to(),
			show=stanza.get_show(),
			status=stanza.get_status()
			);
		self.stream.send(p)
		return 1

	def presence_control(self,stanza):
		p=stanza.make_accept_response()
		self.stream.send(p)
		return 1

if len(sys.argv)<5:
	print "Usage:"
	print "\t%s name secret server port" % (sys.argv[0],)
	print "example:"
	print "\t%s echo.localhost verysecret localhost 5347" % (sys.argv[0],)
	sys.exit(1)

print "creating component..."
c=Component(JID(sys.argv[1]),sys.argv[2],sys.argv[3],int(sys.argv[4]),type="x-echo")

print "connecting..."
c.connect()

print "looping..."
try:
	c.loop(1)
except KeyboardInterrupt:
	print "disconnecting..."
	c.disconnect()
	pass

print "exiting..."
