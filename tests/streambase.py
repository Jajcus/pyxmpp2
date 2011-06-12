#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import time
import re
import logging

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.streambase import StreamBase, XMPPEventHandler
from pyxmpp2.streamevents import *
from pyxmpp2.exceptions import StreamParseError
from pyxmpp2.jid import JID
from pyxmpp2 import ioevents
from pyxmpp2.transport import TCPTransport

from test_util import NetworkTestCase

C2S_SERVER_STREAM_HEAD = '<stream:stream version="1.0" from="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'
C2S_CLIENT_STREAM_HEAD = '<stream:stream version="1.0" to="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'

STREAM_TAIL = '</stream:stream>'
        
PARSE_ERROR_RESPONSE = ('<stream:error><not-well-formed'
                    '  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/>'
                                        '</stream:error></stream:stream>')

TIMEOUT = 5.0 # seconds

logger = logging.getLogger("pyxmpp.test.streambase")

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

class TestInitiatorSelect(NetworkTestCase):
    def setUp(self):
        self.stream = None
        self.transport = None

    def start_transport(self):
        self.transport = TCPTransport()
        self.make_loop()
        self._loop.add_io_handler(self.transport)

    def connect_transport(self):
        addr, port = self.start_server()
        self.transport.connect(addr, port)

    def make_loop(self):
        self._loop = ioevents.SelectMainLoop()

    def tearDown(self):
        self._loop = None
        self.stream = None

    def wait(self, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while self.transport._state not in ("closed", "aborted"):
            self._loop.loop_iteration(0.1)
            if expect:
                match = expect.match(self.server.rdata)
                if match:
                    return match.group(1)
            if time.time() > timeout:
                break

    def wait_short(self, timeout = 0.1):
        self._loop.loop_iteration(timeout)

    def test_connect_close(self):
        handler = JustConnectEventHandler()
        self.stream = StreamBase(u"jabber:client", [handler])
        self.start_transport()
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.wait()
        self.assertFalse(self.stream.connected())
        event_classes = [e.__class__ for e in handler.events_received]
        print repr(event_classes)
        self.assertEqual(event_classes, [ConnectingEvent,
                                            ConnectedEvent, DisconnectedEvent])

    def test_stream_connect_disconnect(self):
        handler = JustStreamConnectEventHandler()
        self.stream = StreamBase(u"jabber:client", [handler])
        self.start_transport()
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.wait_short(0.5)
        self.assertTrue(self.stream.connected())
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(STREAM_TAIL)
        self.wait()
        self.assertFalse(self.stream.connected())
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                                    StreamConnectedEvent, DisconnectedEvent])
 
    def test_parse_error(self):
        handler = IgnoreEventHandler()
        self.stream = StreamBase(u"jabber:client", [handler])
        self.start_transport()
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.wait_short()
        self.server.write("</stream:test>")
        with self.assertRaises(StreamParseError):
            self.wait()
        self.assertFalse(self.stream.connected())
        self.wait_short()
        self.server.wait(1)
        self.assertTrue(self.server.eof)
        self.assertTrue(self.server.rdata.endswith(PARSE_ERROR_RESPONSE))
        self.server.close()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                                    StreamConnectedEvent, DisconnectedEvent])

@unittest.skipIf(not hasattr(ioevents, "PollMainLoop"), "No poll() support")
class TestInitiatorPoll(TestInitiatorSelect):
    def make_loop(self):
        self._loop = ioevents.PollMainLoop()

class TestInitiatorThreaded(TestInitiatorSelect):
    def start_transport(self):
        self.transport = TCPTransport()
        self._reader =  ioevents.ReadingThread(self.transport)
        self._writter =  ioevents.WrittingThread(self.transport)
        self._writter.start()
        self._reader.start()

    def tearDown(self):
        TestInitiatorSelect.tearDown(self)
        self._reader.stop()
        self._reader = None
        self._writter.stop()
        self._writter = None
        time.sleep(0.01)

    def wait(self, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while self._reader.thread.is_alive() or self._writter.thread.is_alive():
            time.sleep(0.1)
            if expect:
                match = expect.match(self.server.rdata)
                if match:
                    return match.group(1)
            if time.time() > timeout:
                break

    def wait_short(self, timeout = 0.1):
        time.sleep(timeout)

class TestReceiverSelect(NetworkTestCase):
    def setUp(self):
        self.make_loop()

    def make_loop(self):
        self._loop = ioevents.SelectMainLoop()

    def tearDown(self):
        self._loop = None
        self.stream = None

    def loop(self, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while self.transport._state not in ("closed", "aborted"):
            self._loop.loop_iteration(0.1)
            if expect:
                match = expect.match(self.client.rdata)
                if match:
                    return match.group(1)
            if time.time() > timeout:
                break

    def loop_iter(self, timeout):
        self._loop.loop_iteration(0.1)

    def test_stream_connect_disconnect(self):
        sock = self.make_listening_socket()
        self.start_client(sock.getsockname())
        handler = JustStreamConnectEventHandler()
        self.stream = StreamBase(u"jabber:client", [handler])
        self.transport = TCPTransport(sock = sock.accept()[0])
        self._loop.add_io_handler(self.transport)
        self.stream.receive(self.transport, sock.getsockname()[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        self.loop_iter(1)
        self.client.write(STREAM_TAIL)
        self.loop()
        self.assertFalse(self.stream.connected())
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [StreamConnectedEvent,
                                                            DisconnectedEvent])

    def test_parse_error(self):
        sock = self.make_listening_socket()
        self.start_client(sock.getsockname())
        handler = IgnoreEventHandler()
        self.stream = StreamBase(u"jabber:client", [handler])
        self.transport = TCPTransport(sock = sock.accept()[0])
        self._loop.add_io_handler(self.transport)
        self.stream.receive(self.transport, sock.getsockname()[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        self.loop_iter(1)
        self.client.write("</stream:test>")
        with self.assertRaises(StreamParseError):
            self.loop()
        self.assertFalse(self.stream.connected())
        self.loop_iter(1)
        self.client.wait(1)
        self.assertTrue(self.client.eof)
        self.assertTrue(self.client.rdata.endswith(PARSE_ERROR_RESPONSE))
        self.client.close()
        self.loop_iter(1)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [StreamConnectedEvent, 
                                                            DisconnectedEvent])

@unittest.skipIf(not hasattr(ioevents, "PollMainLoop"), "No poll() support")
class TestReceiverPoll(TestReceiverSelect):
    def make_loop(self):
        self._loop = ioevents.PollMainLoop()

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestInitiatorSelect))
     suite.addTest(unittest.makeSuite(TestReceiverSelect))
     suite.addTest(unittest.makeSuite(TestInitiatorPoll))
     suite.addTest(unittest.makeSuite(TestReceiverPoll))
     #suite.addTest(unittest.makeSuite(TestInitiatorThreaded))
     return suite

if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.ERROR)
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
