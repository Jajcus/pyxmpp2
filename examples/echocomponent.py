#!/usr/bin/python -u
#
# This example is a simple "echo" component
#
# After connecting to jabberd it will echo messages and presence. This
# component also has basic Disco support (implemented in
# pyxmpp.jabberd.Component class), jabber:iq:vesion and dummy jabber:iq:register.
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
import logging

from pyxmpp.all import JID,Iq,Presence,Message,StreamError,FeatureNotImplementedProtocolError
import pyxmpp.jabberd.all

class Component(pyxmpp.jabberd.Component):
    """Simple component example. Uses `pyxmpp.jabberd.compontent.Component` class
    as base. That class provides basic stream setup (including authentication)
    and Service Discovery server."""

    def __init__(self, jid, secret, server, port):

        # setup componet with provided connection information
        # and identity data
        pyxmpp.jabberd.Component.__init__(self, jid, secret, server, port,
                disco_name="PyXMPP example: echo component",
                disco_category="x-service", disco_type="x-echo")

        # register features to be announced via Service Discovery
        self.disco_info.add_feature("jabber:iq:version")
        self.disco_info.add_feature("jabber:iq:register")

    def stream_state_changed(self,state,arg):
        """This one is called when the state of stream connecting the component
        to a server changes. This will usually be used to let the administrator
        know what is going on."""
        print "*** State changed: %s %r ***" % (state,arg)

    def authenticated(self):
        """This is called when the stream is successfully authenticated.
        That is the best place to setup various handlers for the stream.
        Do not forget about calling the authenticated() method of the base
        class!"""

        pyxmpp.jabberd.Component.authenticated(self)

        # set up handlers for supported <iq/> queries
        self.stream.set_iq_get_handler("query","jabber:iq:version",self.get_version)
        self.stream.set_iq_get_handler("query","jabber:iq:register",self.get_register)
        self.stream.set_iq_set_handler("query","jabber:iq:register",self.set_register)

        # set up handlers for <presence/> stanzas
        self.stream.set_presence_handler("available",self.presence)
        self.stream.set_presence_handler("subscribe",self.presence_control)
        self.stream.set_presence_handler("unsubscribe",self.presence_control)

        # set up handler for <message stanza>
        self.stream.set_message_handler("normal",self.message)

    def get_version(self,iq):
        """Handler for jabber:iq:version queries.

        jabber:iq:version queries are not supported directly by PyXMPP, so the
        XML node is accessed directly through the libxml2 API.  This should be
        used very carefully!"""
        iq=iq.make_result_response()
        q=iq.new_query("jabber:iq:version")
        q.newTextChild(q.ns(),"name","Echo component")
        q.newTextChild(q.ns(),"version","1.0")
        self.stream.send(iq)
        return True

    def get_register(self,iq):
        """Handler for jabber:iq:register 'get' queries.

        jabber:iq:register queries are also not supported directly by PyXMPP,
        see above."""
        to=iq.get_to()
        if to and to!=self.jid:
            raise FeatureNotImplementedProtocolError, "Tried to register at non-null node"
        iq=iq.make_result_response()
        q=iq.new_query("jabber:iq:register")
        q.newTextChild(q.ns(),"instructions","Enter anything below.")
        q.newChild(q.ns(),"username",None)
        q.newChild(q.ns(),"password",None)
        self.stream.send(iq)
        return True

    def set_register(self,iq):
        """Handler for jabber:iq:register 'set' queries.

        This does not do anything usefull (registration data is ignored),
        but shows how to parse request and use Presence stanzas for
        subscription handling."""
        to=iq.get_to()
        if to and to!=self.jid:
            raise FeatureNotImplementedProtocolError, "Tried to register at non-null node"
        remove=iq.xpath_eval("r:query/r:remove",{"r":"jabber:iq:register"})
        if remove:
            m=Message(from_jid=iq.get_to(),to_jid=iq.get_from(),stanza_type="chat",
                    body=u"Unregistered")
            self.stream.send(m)
            p=Presence(from_jid=iq.get_to(),to_jid=iq.get_from(),stanza_type="unsubscribe")
            self.stream.send(p)
            p=Presence(from_jid=iq.get_to(),to_jid=iq.get_from(),stanza_type="unsubscribed")
            self.stream.send(p)
            return True
        username=iq.xpath_eval("r:query/r:username",{"r":"jabber:iq:register"})
        if username:
            username=username[0].getContent()
        else:
            username=u""
        password=iq.xpath_eval("r:query/r:password",{"r":"jabber:iq:register"})
        if password:
            password=password[0].getContent()
        else:
            password=u""
        m=Message(from_jid=iq.get_to(),to_jid=iq.get_from(),stanza_type="chat",
                body=u"Registered with username '%s' and password '%s'"
                " (both ignored)" % (username,password))
        self.stream.send(m)
        p=Presence(from_jid=iq.get_to(),to_jid=iq.get_from(),stanza_type="subscribe")
        self.stream.send(p)
        iq=iq.make_result_response()
        self.stream.send(iq)
        return True

    def message(self,stanza):
        """Message handler for the component.

        Just echoes the message back if its type is not 'error' or
        'headline'. Please note that all message types but 'error' will
        be passed to the handler for 'normal' message unless some dedicated
        handler process them.

        :returns: `True` to indicate, that the stanza should not be processed
        any further."""
        if stanza.get_type()=="headline":
            return True
        subject=stanza.get_subject()
        if subject:
            subject=u"Re: "+subject
        m=Message(
            to_jid=stanza.get_from(),
            from_jid=stanza.get_to(),
            stanza_type=stanza.get_type(),
            subject=subject,
            body=stanza.get_body())
        self.stream.send(m)
        return True

    def presence(self,stanza):
        """Handle 'available' (without 'type') and 'unavailable' <presence/>
        stanzas -- echo them back."""
        p=Presence(
            stanza_type=stanza.get_type(),
            to_jid=stanza.get_from(),
            from_jid=stanza.get_to(),
            show=stanza.get_show(),
            status=stanza.get_status()
            );
        self.stream.send(p)
        return True

    def presence_control(self,stanza):
        """Handle subscription control <presence/> stanzas -- acknowledge
        them."""
        p=stanza.make_accept_response()
        self.stream.send(p)
        return True

# PyXMPP uses `logging` module for its debug output
# applications should set it up as needed
logger=logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

if len(sys.argv)<5:
    print "Usage:"
    print "\t%s name secret server port" % (sys.argv[0],)
    print "example:"
    print "\t%s echo.localhost verysecret localhost 5347" % (sys.argv[0],)
    sys.exit(1)

print "creating component..."
c=Component(JID(sys.argv[1]),sys.argv[2],sys.argv[3],int(sys.argv[4]))

print "connecting..."
c.connect()

print "looping..."
try:
    # Component class provides basic "main loop" for the applitation
    # Though, most applications would need to have their own loop and call
    # component.stream.loop_iter() from it whenever an event on
    # component.stream.fileno() occurs.
    c.loop(1)
except KeyboardInterrupt:
    print "disconnecting..."
    c.disconnect()
    pass

print "exiting..."
# vi: sts=4 et sw=4
