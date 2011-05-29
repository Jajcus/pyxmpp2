#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import time
import re

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.streambase import StreamBase, XMPPEventHandler
from pyxmpp2.streamevents import *
from pyxmpp2.exceptions import StreamParseError
from pyxmpp2.jid import JID

from test_util import NetworkTestCase

C2S_SERVER_STREAM_HEAD = '<stream:stream version="1.0" from="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'
C2S_CLIENT_STREAM_HEAD = '<stream:stream version="1.0" to="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'

STREAM_TAIL = '</stream:stream>'
        
PARSE_ERROR_RESPONSE = ('<stream:error><xml-not-well-formed'
                    '  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/>'
                                        '</stream:error></stream:stream>')

TIMEOUT = 1.0 # seconds

class JustConnectEventHandler(XMPPEventHandler):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
        if isinstance(event, ConnectedEvent):
            event.stream.close()
            return True
        return False

class JustStreamConnectEventHandler(XMPPEventHandler):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
        if isinstance(event, StreamConnectedEvent):
            event.stream.disconnect()
            return True
        return False

class AuthorizedEventHandler(XMPPEventHandler):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
        if isinstance(event, AuthorizedEvent):
            event.stream.close()
            return True
        return False

class IgnoreEventHandler(XMPPEventHandler):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
        return False

class JustAcceptEventHandler(XMPPEventHandler):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
        if isinstance(event, ConnectionAcceptedEvent):
            event.stream.close()
            return True
        return False

class TestInitiator(NetworkTestCase):
    def loop(self, stream, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while stream.socket and time.time() < timeout:
            stream.loop_iter(0.1)
            if expect:
                match = expect.match(self.server.rdata)
                if match:
                    return match.group(1)

    def test_connect_close(self):
        addr, port = self.start_server()
        handler = JustConnectEventHandler()
        stream = StreamBase(u"jabber:client", [handler])
        stream.connect(addr, port)
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                                            ConnectedEvent, DisconnectedEvent])
    def test_stream_connect_disconnect(self):
        addr, port = self.start_server()
        handler = JustStreamConnectEventHandler()
        stream = StreamBase(u"jabber:client", [handler])
        stream.connect(addr, port)
        self.server.write(C2S_SERVER_STREAM_HEAD)
        stream.loop_iter(1)
        self.server.write(STREAM_TAIL)
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, DisconnectedEvent])
 
    def test_parse_error(self):
        addr, port = self.start_server()
        handler = JustStreamConnectEventHandler()
        stream = StreamBase(u"jabber:client", [handler])
        stream.connect(addr, port)
        self.server.write(C2S_SERVER_STREAM_HEAD)
        stream.loop_iter(1)
        self.server.write("</stream:test>")
        with self.assertRaises(StreamParseError):
            self.loop(stream)
        self.assertIsNone(stream.socket)
        self.server.wait(1)
        self.assertTrue(self.server.eof)
        self.assertTrue(self.server.rdata.endswith(PARSE_ERROR_RESPONSE))
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, DisconnectedEvent])
 
class TestReceiver(NetworkTestCase):
    def loop(self, stream, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while stream.socket and time.time() < timeout:
            stream.loop_iter(0.1)
            if expect:
                match = expect.match(self.client.rdata)
                if match:
                    return match.group(1)

    def test_accept_close(self):
        sock = self.make_listening_socket()
        self.start_client(sock.getsockname())
        handler = JustAcceptEventHandler()
        stream = StreamBase(u"jabber:client", [handler])
        stream.accept(sock, sock.getsockname()[0])
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectionAcceptedEvent, 
                                                            DisconnectedEvent])

    def test_stream_connect_disconnect(self):
        sock = self.make_listening_socket()
        self.start_client(sock.getsockname())
        handler = JustStreamConnectEventHandler()
        stream = StreamBase(u"jabber:client", [handler])
        stream.accept(sock, sock.getsockname()[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        stream.loop_iter(1)
        self.client.write(STREAM_TAIL)
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectionAcceptedEvent,
                                    StreamConnectedEvent, DisconnectedEvent])
 
    def test_parse_error(self):
        sock = self.make_listening_socket()
        self.start_client(sock.getsockname())
        handler = JustStreamConnectEventHandler()
        stream = StreamBase(u"jabber:client", [handler])
        stream.accept(sock, sock.getsockname()[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        stream.loop_iter(1)
        self.client.write("</stream:test>")
        with self.assertRaises(StreamParseError):
            self.loop(stream)
        self.assertIsNone(stream.socket)
        self.client.wait(1)
        self.assertTrue(self.client.eof)
        self.assertTrue(self.client.rdata.endswith(PARSE_ERROR_RESPONSE))
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectionAcceptedEvent,
                                    StreamConnectedEvent, DisconnectedEvent])
 
def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestInitiator))
     suite.addTest(unittest.makeSuite(TestReceiver))
     return suite

if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.ERROR)
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
