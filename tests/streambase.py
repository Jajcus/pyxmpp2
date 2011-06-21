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
from pyxmpp2.transport import TCPTransport

from pyxmpp2.mainloop.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.mainloop.select import SelectMainLoop
from pyxmpp2.mainloop.poll import PollMainLoop
from pyxmpp2.mainloop.threads import ThreadPool

from test_util import NetworkTestCase

C2S_SERVER_STREAM_HEAD = '<stream:stream version="1.0" from="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'
C2S_CLIENT_STREAM_HEAD = '<stream:stream version="1.0" to="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'

STREAM_TAIL = '</stream:stream>'
        
PARSE_ERROR_RESPONSE = ('<stream:error><not-well-formed'
                    '  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/>'
                                        '</stream:error></stream:stream>')

TIMEOUT = 5.0 # seconds

logger = logging.getLogger("pyxmpp.test.streambase")

class EventRecorder(EventHandler):
    def __init__(self):
        self.events_received = []
    @event_handler()
    def handle_event(self, event):
        self.events_received.append(event)
        return False
    @event_handler(DisconnectedEvent)
    def handle_disconnected_event(self, event):
        event.stream.event(QUIT)

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

class TestInitiatorSelect(NetworkTestCase):
    def setUp(self):
        NetworkTestCase.setUp(self)
        self.stream = None
        self.transport = None
        self.loop = None

    def start_transport(self, handlers):
        self.transport = TCPTransport()
        self.make_loop(handlers + [self.transport])

    def connect_transport(self):
        addr, port = self.start_server()
        self.transport.connect(addr, port)

    def make_loop(self, handlers):
        self.loop = SelectMainLoop(None, handlers)

    def tearDown(self):
        NetworkTestCase.tearDown(self)
        self.loop = None
        self.stream = None
        self.transport = None

    def wait(self, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while not self.loop.finished():
            self.loop.loop_iteration(0.1)
            if expect:
                match = expect.match(self.server.rdata)
                if match:
                    return match.group(1)
            if time.time() > timeout:
                break

    def wait_short(self, timeout = 0.1):
        self.loop.loop_iteration(timeout)

    def test_connect_close(self):
        handler = JustConnectEventHandler()
        self.stream = StreamBase(u"jabber:client", [])
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
        self.stream = StreamBase(u"jabber:client", [])
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
        self.stream = StreamBase(u"jabber:client", [])
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
        self.server.close()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        
        # when exception was raised by a thread DisconnectedEvent won't
        # be sent
        if event_classes[-1] == DisconnectedEvent:
            event_classes = event_classes[:-1]

        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                                    StreamConnectedEvent])

@unittest.skipIf(not hasattr(select, "poll"), "No poll() support")
class TestInitiatorPoll(TestInitiatorSelect):
    def make_loop(self, handlers):
        self.loop = PollMainLoop(None, handlers)

class TestInitiatorThreaded(TestInitiatorSelect):
    def make_loop(self, handlers):
        self.loop = ThreadPool(None, handlers)

    def connect_transport(self):
        TestInitiatorSelect.connect_transport(self)
        self.loop.start()

    def tearDown(self):
        if self.loop:
            logger.debug("Stopping the thread pool")
            try:
                self.loop.stop(True, 2)
            except Exception:
                logger.exception("self.loop.stop failed:")
            else:
                logger.debug("  done (or timed out)")
            self.loop.event_dispatcher.flush(False)
        TestInitiatorSelect.tearDown(self)

class TestReceiverSelect(NetworkTestCase):
    def setUp(self):
        NetworkTestCase.setUp(self)
        self.stream = None
        self.transport = None
        self.loop = None
        self.addr = None

    def start_transport(self, handlers):
        sock = self.make_listening_socket()
        self.addr = sock.getsockname()
        self.start_client(self.addr)
        self.transport = TCPTransport(sock = sock.accept()[0])
        self.make_loop(handlers + [self.transport])

    def make_loop(self, handlers):
        self.loop = SelectMainLoop(None, handlers)

    def tearDown(self):
        NetworkTestCase.tearDown(self)
        self.loop = None
        self.stream = None
        self.transport = None

    def wait(self, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while not self.loop.finished():
            self.loop.loop_iteration(0.1)
            if expect:
                match = expect.match(self.client.rdata)
                if match:
                    return match.group(1)
            if time.time() > timeout:
                break

    def wait_short(self, timeout = 0.1):
        self.loop.loop_iteration(timeout)

    def tearDown(self):
        self.loop = None
        self.stream = None

    def test_stream_connect_disconnect(self):
        handler = JustStreamConnectEventHandler()
        self.start_transport([handler])
        self.stream = StreamBase(u"jabber:client", [])
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
        self.stream = StreamBase(u"jabber:client", [])
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
class TestReceiverPoll(TestReceiverSelect):
    def make_loop(self, handlers):
        self.loop = PollMainLoop(None, handlers)

class TestReceiverThreaded(TestReceiverSelect):
    def make_loop(self, handlers):
        self.loop = ThreadPool(None, handlers)

    def start_transport(self, handlers):
        TestReceiverSelect.start_transport(self, handlers)
        self.loop.start()

    def tearDown(self):
        if self.loop:
            logger.debug("Stopping the thread pool")
            try:
                self.loop.stop(True, 2)
            except Exception:
                logger.exception("self.loop.stop failed:")
            else:
                logger.debug("  done (or timed out)")
            self.loop.event_dispatcher.flush(False)
        TestReceiverSelect.tearDown(self)

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
