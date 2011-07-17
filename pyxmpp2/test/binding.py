#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest
import re

from pyxmpp2.streambase import StreamBase
from pyxmpp2.streamevents import * # pylint: disable=W0401,W0614
from pyxmpp2.jid import JID
from pyxmpp2.binding import ResourceBindingHandler
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.stanzaprocessor import StanzaProcessor

from pyxmpp2.interfaces import event_handler

from pyxmpp2.test._util import EventRecorder
from pyxmpp2.test._util import InitiatorSelectTestCase
from pyxmpp2.test._util import ReceiverSelectTestCase

C2S_SERVER_STREAM_HEAD = ('<stream:stream version="1.0"'
                            ' from="127.0.0.1"'
                            ' xmlns:stream="http://etherx.jabber.org/streams"'
                            ' xmlns="jabber:client">')
C2S_CLIENT_STREAM_HEAD = ('<stream:stream version="1.0"'
                            ' to="127.0.0.1"'
                            ' xmlns:stream="http://etherx.jabber.org/streams"'
                            ' xmlns="jabber:client">')

BIND_FEATURES = """<stream:features>
     <bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'/>
</stream:features>"""

BIND_GENERATED_REQUEST = """<iq type="set" id="42">
  <bind  xmlns="urn:ietf:params:xml:ns:xmpp-bind">
  </bind>
</iq>
"""

BIND_GENERATED_RESPONSE = """<iq type="result" id="{0}">
  <bind  xmlns="urn:ietf:params:xml:ns:xmpp-bind">
    <jid>test@127.0.0.1/Generated</jid>
  </bind>
</iq>
"""

BIND_PROVIDED_REQUEST = """<iq type="set" id="42">
  <bind  xmlns="urn:ietf:params:xml:ns:xmpp-bind">
    <resource>Provided</resource>
  </bind>
</iq>
"""

BIND_PROVIDED_RESPONSE = """<iq type="result" id="{0}">
  <bind  xmlns="urn:ietf:params:xml:ns:xmpp-bind">
    <jid>test@127.0.0.1/Provided</jid>
  </bind>
</iq>
"""


STREAM_TAIL = '</stream:stream>'
        
PARSE_ERROR_RESPONSE = ('<stream:error><xml-not-well-formed'
                    '  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/>'
                                        '</stream:error></stream:stream>')

TIMEOUT = 1.0 # seconds

class AuthorizedEventHandler(EventRecorder):
    @event_handler(AuthorizedEvent)
    def handle_authorized_event(self, event):
        # pylint: disable=R0201
        event.stream.close()
        return True

class TestBindingInitiator(InitiatorSelectTestCase):
    def test_bind_no_resource(self):
        handler = AuthorizedEventHandler()
        handlers = [ResourceBindingHandler(), handler]
        processor = StanzaProcessor()
        processor.setup_stanza_handlers(handlers, "post-auth")
        self.stream = StreamBase(u"jabber:client", processor, handlers)
        processor.uplink = self.stream
        self.stream.me = JID("test@127.0.0.1")
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.wait_short(1)
        self.server.write(BIND_FEATURES)
        req_id = self.wait(1,
                    expect = re.compile(r".*<iq[^>]*id=[\"']([^\"']*)[\"']"))
        self.assertIsNotNone(req_id)
        self.server.write(BIND_GENERATED_RESPONSE.format(req_id))
        self.wait()
        self.assertFalse(self.stream.is_connected())
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    BindingResourceEvent, AuthorizedEvent, DisconnectedEvent])
 
    def test_bind(self):
        handler = AuthorizedEventHandler()
        handlers = [ResourceBindingHandler(), handler]
        processor = StanzaProcessor()
        processor.setup_stanza_handlers(handlers, "post-auth")
        self.stream = StreamBase(u"jabber:client", processor, handlers,
                                        XMPPSettings({"resource": "Provided"}))
        processor.uplink = self.stream
        self.stream.me = JID("test@127.0.0.1")
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.wait_short(1)
        self.server.write(BIND_FEATURES)
        req_id = self.wait(1,
                    expect = re.compile(r".*<iq[^>]*id=[\"']([^\"']*)[\"'].*"
                                            r"<resource>Provided</resource>"))
        self.assertIsNotNone(req_id)
        self.server.write(BIND_PROVIDED_RESPONSE.format(req_id))
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    BindingResourceEvent, AuthorizedEvent, DisconnectedEvent])
   
class TestBindingReceiver(ReceiverSelectTestCase):
    def test_bind_no_resource(self):
        handler = EventRecorder()
        handlers = [ResourceBindingHandler(), handler]
        processor = StanzaProcessor()
        self.start_transport(handlers)
        self.stream = StreamBase(u"jabber:client", processor, handlers)
        processor.uplink = self.stream
        self.stream.receive(self.transport, self.addr[0])
        self.stream.set_peer_authenticated(JID("test@127.0.0.1"))
        processor.setup_stanza_handlers(handlers, "post-auth")
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        features = self.wait(
                expect = re.compile(r".*<stream:features>"
                        r"(.*<bind.*urn:ietf:params:xml:ns:xmpp-bind.*)"
                                                    r"</stream:features>"))
        self.assertIsNotNone(features)
        self.client.write(BIND_GENERATED_REQUEST)
        resource = self.wait(
                expect = re.compile(r".*<iq.*id=(?:\"42\"|'42').*>"
                            r"<bind.*<jid>test@127.0.0.1/(.*)</jid>.*</bind>"))
        self.assertTrue(resource)
        self.client.write(STREAM_TAIL)
        self.client.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [AuthenticatedEvent,
                    StreamConnectedEvent, AuthorizedEvent, DisconnectedEvent])
 
    def test_bind_resource(self):
        handler = EventRecorder()
        handlers = [ResourceBindingHandler(), handler]
        processor = StanzaProcessor()
        self.start_transport(handlers)
        self.stream = StreamBase(u"jabber:client", processor, handlers)
        processor.uplink = self.stream
        self.stream.receive(self.transport, self.addr[0])
        self.stream.set_peer_authenticated(JID("test@127.0.0.1"))
        processor.setup_stanza_handlers(handlers, "post-auth")
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        features = self.wait(
                expect = re.compile(r".*<stream:features>"
                    r"(.*<bind.*urn:ietf:params:xml:ns:xmpp-bind.*)"
                                                    r"</stream:features>"))
        self.assertIsNotNone(features)
        self.client.write(BIND_PROVIDED_REQUEST)
        resource = self.wait(
                expect = re.compile(r".*<iq.*id=(?:\"42\"|'42').*>"
                            r"<bind.*<jid>test@127.0.0.1/(.*)</jid>.*</bind>"))
        self.assertEqual(resource, u"Provided")
        self.client.write(STREAM_TAIL)
        self.client.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [AuthenticatedEvent,
                    StreamConnectedEvent, AuthorizedEvent, DisconnectedEvent])

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
