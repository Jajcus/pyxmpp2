#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import time
import re
import logging
import select

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.streambase import StreamBase
from pyxmpp2.streamevents import *
from pyxmpp2.exceptions import StreamParseError
from pyxmpp2.jid import JID
from pyxmpp2.message import Message

from pyxmpp2.mainloop.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.interfaces import StanzaRoute

from test_util import EventRecorder
from test_util import InitiatorSelectTestCase
from test_util import InitiatorPollTestMixIn, InitiatorThreadedTestMixIn
from test_util import ReceiverSelectTestCase
from test_util import ReceiverPollTestMixIn, ReceiverThreadedTestMixIn

C2S_SERVER_STREAM_HEAD = '<stream:stream version="1.0" from="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'
C2S_CLIENT_STREAM_HEAD = '<stream:stream version="1.0" to="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'

STREAM_TAIL = '</stream:stream>'
        
PARSE_ERROR_RESPONSE = ('<stream:error><not-well-formed'
                    '  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/>'
                                        '</stream:error></stream:stream>')

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
        event.stream.close()
        return True

class JustStreamConnectEventHandler(EventRecorder):
    @event_handler(StreamConnectedEvent)
    def handle_stream_conencted_event(self, event):
        event.stream.disconnect()
        return True

class AuthorizedEventHandler(EventRecorder):
    @event_handler(AuthorizedEvent)
    def handle_authorized_event(self, event):
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
        self.wait_short(0.5)
        self.assertTrue(self.stream.is_connected())
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.wait(expect = re.compile(".*(</stream:stream>)"))
        self.server.write(STREAM_TAIL)
        self.server.close()
        self.wait(1)
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
        self.server.write("</stream:test>")
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
       
        # when exception was raised by a thread DisconnectedEvent won't
        # be sent
        if event_classes[-1] == DisconnectedEvent:
            event_classes = event_classes[:-1]

        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                                    StreamConnectedEvent])

    def test_stanza_send(self):
        handler = IgnoreEventHandler()
        route = RecordingRoute()
        self.stream = StreamBase(u"jabber:client", route, [])
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.wait_short(0.5)
        self.assertTrue(self.stream.is_connected())
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.stream.send(Message(to_jid = JID(u"test@example.org"),
                                                            body = u"Test"))
        xml = self.wait(expect = re.compile(".*(<message.*</message>)"))
        self.assertIsNotNone(xml)
        if "xmlns" not in xml:
            xml = xml.replace(u"<message", u"<message xmlns='jabber:client'")
        element = XML(xml)
        stanza = Message(element)
        self.assertEqual(stanza.body, u"Test")
        self.stream.disconnect()
        self.server.write(STREAM_TAIL)
        self.server.close()
        self.wait(1)
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
        self.wait_short(0.5)
        self.assertTrue(self.stream.is_connected())
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write("<message><body>Test</body></message>")
        self.server.write(STREAM_TAIL)
        self.server.disconnect()
        self.wait(expect = re.compile(".*(</stream:stream>)"))
        self.stream.disconnect()
        self.wait(1)
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

class TestInitiatorThreaded(InitiatorThreadedTestMixIn, TestInitiatorSelect):
    pass

class TestReceiverSelect(ReceiverSelectTestCase):
    def test_stream_connect_disconnect(self):
        handler = JustStreamConnectEventHandler()
        self.start_transport([handler])
        self.stream = StreamBase(u"jabber:client", None, [])
        self.stream.receive(self.transport, self.addr[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        self.wait_short(0.5)
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
        self.wait_short(0.2)
        self.client.write("</stream:test>")
        with self.assertRaises(StreamParseError):
            self.wait()
        self.assertFalse(self.stream.is_connected())
        self.wait_short(0.1)
        self.client.wait(1)
        self.assertTrue(self.client.eof)
        self.assertTrue(self.client.rdata.endswith(PARSE_ERROR_RESPONSE))
        self.client.close()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        
        # when exception was raised by a thread DisconnectedEvent won't
        # be sent
        if event_classes[-1] == DisconnectedEvent:
            event_classes = event_classes[:-1]
            
        self.assertEqual(event_classes, [StreamConnectedEvent])

@unittest.skipIf(not hasattr(select, "poll"), "No poll() support")
class TestReceiverPoll(ReceiverPollTestMixIn, TestReceiverSelect):
    pass

class TestReceiverThreaded(ReceiverThreadedTestMixIn, TestReceiverSelect):
    pass

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestInitiatorSelect))
     suite.addTest(unittest.makeSuite(TestReceiverSelect))
     suite.addTest(unittest.makeSuite(TestInitiatorPoll))
     suite.addTest(unittest.makeSuite(TestReceiverPoll))
     suite.addTest(unittest.makeSuite(TestInitiatorThreaded))
     suite.addTest(unittest.makeSuite(TestReceiverThreaded))
     return suite

if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.ERROR)
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
