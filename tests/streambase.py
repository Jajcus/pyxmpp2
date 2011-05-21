#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import time

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.streambase import StreamBase
from pyxmpp2.streamevents import *
from pyxmpp2.exceptions import StreamParseError

from test_util import NetworkTestCase

C2S_SERVER_STREAM_HEAD = '<stream:stream version="1.0" from="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'
C2S_SERVER_STREAM_TAIL = '</stream:stream>'

TIMEOUT = 1.0 # seconds

class JustConnectEventHandler(object):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
        if isinstance(event, ConnectedEvent):
            event.stream.close()
            return True
        return False

class JustStreamConnectEventHandler(object):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
        if isinstance(event, StreamConnectedEvent):
            event.stream.disconnect()
            return True
        return False


class TestInitiator(NetworkTestCase):
    def loop(self, stream):
        timeout = time.time() + TIMEOUT
        while stream.socket and time.time() < timeout:
            stream.loop_iter(1)

    def test_connect_close(self):
        addr, port = self.start_server()
        handler = JustConnectEventHandler()
        stream = StreamBase(u"jabber:client", event_handler = handler)
        stream.connect(addr, port)
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                                            ConnectedEvent, DisconnectedEvent])
    def test_stream_connect_disconnect(self):
        addr, port = self.start_server()
        handler = JustStreamConnectEventHandler()
        stream = StreamBase(u"jabber:client", event_handler = handler)
        stream.connect(addr, port)
        self.server.write(C2S_SERVER_STREAM_HEAD)
        stream.loop_iter(1)
        self.server.write(C2S_SERVER_STREAM_TAIL)
        self.loop(stream)
        self.assertIsNone(stream.socket)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, DisconnectedEvent])
    
    def test_parse_error(self):
        addr, port = self.start_server()
        handler = JustStreamConnectEventHandler()
        stream = StreamBase(u"jabber:client", event_handler = handler)
        stream.connect(addr, port)
        self.server.write(C2S_SERVER_STREAM_HEAD)
        stream.loop_iter(1)
        self.server.write("</stream:test>")
        with self.assertRaises(StreamParseError):
            self.loop(stream)
        self.assertIsNone(stream.socket)
        self.server.wait(1)
        self.assertTrue(self.server.eof)
        self.assertTrue(self.server.rdata.endswith('<stream:error><xml-not-well-formed  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/></stream:error></stream:stream>'))
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, DisconnectedEvent])
 
def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestInitiator))
     return suite

if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.ERROR)
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
