#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest
import re
import logging
import select

from xml.etree.ElementTree import XML

try:
    import glib
except ImportError:
    # pylint: disable=C0103
    glib = None

from pyxmpp2.streambase import StreamBase
from pyxmpp2.streamevents import * # pylint: disable=W0401,W0614
from pyxmpp2.exceptions import StreamParseError
from pyxmpp2.jid import JID
from pyxmpp2.message import Message
from pyxmpp2.settings import XMPPSettings

from pyxmpp2.interfaces import event_handler
from pyxmpp2.interfaces import StanzaRoute

from pyxmpp2.test._util import EventRecorder
from pyxmpp2.test._util import InitiatorSelectTestCase
from pyxmpp2.test._util import InitiatorPollTestMixIn
from pyxmpp2.test._util import InitiatorThreadedTestMixIn
from pyxmpp2.test._util import InitiatorGLibTestMixIn, ReceiverGLibTestMixIn
from pyxmpp2.test._util import ReceiverSelectTestCase
from pyxmpp2.test._util import ReceiverPollTestMixIn, ReceiverThreadedTestMixIn

C2S_SERVER_STREAM_HEAD = (b'<stream:stream version="1.0"'
                            b' from="127.0.0.1"'
                            b' xmlns:stream="http://etherx.jabber.org/streams"'
                            b' xmlns="jabber:client">')
C2S_CLIENT_STREAM_HEAD = (b'<stream:stream version="1.0"'
                            b' to="127.0.0.1"'
                            b' xmlns:stream="http://etherx.jabber.org/streams"'
                            b' xmlns="jabber:client">')

STREAM_TAIL = b'</stream:stream>'

PARSE_ERROR_RESPONSE = (b'<stream:error><not-well-formed'
                    b'  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/>'
                                        b'</stream:error></stream:stream>')

logger = logging.getLogger("pyxmpp2.test.streambase")

class RecordingRoute(StanzaRoute):
    def __init__(self):
        self.received = []
        self.sent = []
    def send(self, stanza):
        self.sent.append(stanza)
    def uplink_receive(self, stanza):
        self.received.append(stanza)

class JustConnectEventHandler(EventRecorder):
    @event_handler(ConnectedEvent)
    def handle_connected_event(self, event):
        # pylint: disable=R0201
        event.stream.close()
        return True

class JustStreamConnectEventHandler(EventRecorder):
    @event_handler(StreamConnectedEvent)
    def handle_stream_conencted_event(self, event):
        # pylint: disable=R0201
        event.stream.disconnect()
        return True

class AuthorizedEventHandler(EventRecorder):
    @event_handler(AuthorizedEvent)
    def handle_authorized_event(self, event):
        # pylint: disable=R0201
        event.stream.close()
        return True

class IgnoreEventHandler(EventRecorder):
    pass

class TestInitiatorSelect(InitiatorSelectTestCase):
    def test_connect_close(self):
        handler = JustConnectEventHandler()
        self.stream = StreamBase(u"jabber:client", None, [])
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.wait()
        self.assertFalse(self.stream.is_connected())
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent,
                                            ConnectedEvent, DisconnectedEvent])

    def test_stream_connect_disconnect(self):
        handler = JustStreamConnectEventHandler()
        self.stream = StreamBase(u"jabber:client", None, [])
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.wait_short(0.25)
        self.wait_short(0.25)
        self.assertTrue(self.stream.is_connected())
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.wait(expect = re.compile(b".*(</stream:stream>)"))
        self.server.write(STREAM_TAIL)
        self.server.disconnect()
        self.wait()
        self.assertFalse(self.stream.is_connected())
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                                    StreamConnectedEvent, DisconnectedEvent])

    def test_parse_error(self):
        handler = IgnoreEventHandler()
        self.stream = StreamBase(u"jabber:client", None, [])
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.wait_short()
        self.server.write(b"</stream:test>")
        with self.assertRaises(StreamParseError):
            logger.debug("-- WAIT start")
            self.wait()
            logger.debug("-- WAIT end")
        self.assertFalse(self.stream.is_connected())
        self.wait_short()
        self.server.wait(1)
        self.assertTrue(self.server.eof)
        self.assertTrue(self.server.rdata.endswith(PARSE_ERROR_RESPONSE))
        self.server.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                                    StreamConnectedEvent, DisconnectedEvent])

    def test_stanza_send(self):
        handler = IgnoreEventHandler()
        route = RecordingRoute()
        self.stream = StreamBase(u"jabber:client", route, [])
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.wait_short(0.25)
        self.wait_short(0.25)
        self.assertTrue(self.stream.is_connected())
        self.stream.send(Message(to_jid = JID(u"test@example.org"),
                                                            body = u"Test"))
        xml = self.wait(expect = re.compile(b".*(<message.*</message>)"))
        self.assertIsNotNone(xml)
        if b"xmlns" not in xml:
            xml = xml.replace(b"<message", b"<message xmlns='jabber:client'")
        element = XML(xml)
        stanza = Message(element)
        self.assertEqual(stanza.body, u"Test")
        self.stream.disconnect()
        self.server.write(STREAM_TAIL)
        self.server.disconnect()
        self.wait()
        self.assertEqual(route.sent, [])
        self.assertEqual(route.received, [])
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                                    StreamConnectedEvent, DisconnectedEvent])

    def test_stanza_receive(self):
        handler = IgnoreEventHandler()
        route = RecordingRoute()
        self.stream = StreamBase(u"jabber:client", route, [])
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        logger.debug("-- waiting for connect")
        self.wait_short(0.25)
        self.wait_short(0.25)
        logger.debug("-- checking connected")
        self.assertTrue(self.stream.is_connected())
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(b"<message><body>Test</body></message>")
        self.server.write(STREAM_TAIL)
        self.server.disconnect()
        self.wait(expect = re.compile(b".*(</stream:stream>)"))
        self.stream.disconnect()
        self.wait()
        self.assertEqual(route.sent, [])
        self.assertEqual(len(route.received), 1)
        stanza = route.received[0]
        self.assertIsInstance(stanza, Message)
        self.assertEqual(stanza.body, u"Test")
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                                    StreamConnectedEvent, DisconnectedEvent])

@unittest.skipIf(not hasattr(select, "poll"), "No poll() support")
class TestInitiatorPoll(InitiatorPollTestMixIn, TestInitiatorSelect):
    pass

@unittest.skipIf(glib is None, "No glib module")
class TestInitiatorGLib(InitiatorGLibTestMixIn, TestInitiatorSelect):
    pass

class TestInitiatorThreaded(InitiatorThreadedTestMixIn, TestInitiatorSelect):
    pass

class TestReceiverSelect(ReceiverSelectTestCase):
    def test_stream_connect_disconnect(self):
        handler = JustStreamConnectEventHandler()
        self.start_transport([handler])
        self.stream = StreamBase(u"jabber:client", None, [])
        self.stream.receive(self.transport, self.addr[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        self.wait_short(0.25)
        self.wait_short(0.25)
        self.client.write(STREAM_TAIL)
        self.wait()
        self.assertFalse(self.stream.is_connected())
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [StreamConnectedEvent,
                                                            DisconnectedEvent])

    def test_parse_error(self):
        handler = IgnoreEventHandler()
        self.start_transport([handler])
        self.stream = StreamBase(u"jabber:client", None, [])
        self.stream.receive(self.transport, self.addr[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        self.wait_short(0.25)
        self.wait_short(0.25)
        self.client.write(b"</stream:test>")
        logger.debug("waiting for exception...")
        with self.assertRaises(StreamParseError):
            self.wait()
        logger.debug(" got it!")
        self.assertFalse(self.stream.is_connected())
        self.wait_short(0.1)
        logger.debug("waiting for connection close...")
        self.client.wait(1)
        logger.debug(" done")
        self.assertTrue(self.client.eof)
        self.assertTrue(self.client.rdata.endswith(PARSE_ERROR_RESPONSE))
        self.client.disconnect()
        logger.debug("final wait...")
        self.wait()
        logger.debug(" done")
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [StreamConnectedEvent,
                                                        DisconnectedEvent])

@unittest.skipIf(not hasattr(select, "poll"), "No poll() support")
class TestReceiverPoll(ReceiverPollTestMixIn, TestReceiverSelect):
    pass

class TestReceiverThreaded(ReceiverThreadedTestMixIn, TestReceiverSelect):
    pass

@unittest.skipIf(glib is None, "No glib module")
class TestReceiverGLib(ReceiverGLibTestMixIn, TestReceiverSelect):
    pass

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
