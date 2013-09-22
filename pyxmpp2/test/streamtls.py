#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest
import re
import os

from pyxmpp2.test._support import DATA_DIR

from xml.etree.ElementTree import XML

from pyxmpp2.streambase import StreamBase
from pyxmpp2.streamtls import StreamTLSHandler
from pyxmpp2.streamevents import *  # pylint: disable=W0614,W0401
from pyxmpp2.exceptions import TLSNegotiationFailed
from pyxmpp2.settings import XMPPSettings

from pyxmpp2.test._util import EventRecorder, InitiatorSelectTestCase

C2S_SERVER_STREAM_HEAD = (b'<stream:stream version="1.0"'
                            b' from="server.example.org"'
                            b' xmlns:stream="http://etherx.jabber.org/streams"'
                            b' xmlns="jabber:client">')
C2S_CLIENT_STREAM_HEAD = (b'<stream:stream version="1.0"'
                            b' to="server.example.org"'
                            b' xmlns:stream="http://etherx.jabber.org/streams"'
                            b' xmlns="jabber:client">')

TLS_FEATURES = b"""<stream:features>
     <starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls' />
</stream:features>"""
TLS_REQUIRED_FEATURES = b"""<stream:features>
     <starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'>
        <required />
     </starttls>
</stream:features>"""


EMPTY_FEATURES = b"""<stream:features/>"""

PROCEED = b"<proceed xmlns='urn:ietf:params:xml:ns:xmpp-tls' />"

STREAM_TAIL = b'</stream:stream>'

class TestInitiator(InitiatorSelectTestCase):
    def test_enabled_optional(self):
        """Test TLS enabled in settings, and optional on the server."""
        settings = XMPPSettings({
                        u"starttls": True,
                        u"tls_cacert_file": os.path.join(DATA_DIR, "ca.pem"),
                                })
        handler = EventRecorder()
        handlers = [StreamTLSHandler(settings), handler]
        self.stream = StreamBase(u"jabber:client", None, handlers, settings)
        self.start_transport(handlers)
        self.stream.initiate(self.transport, to = "server.example.org")
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(TLS_FEATURES)
        xml = self.wait(2, expect = re.compile(br".*(<starttls.*/>)"))
        self.assertIsNotNone(xml)
        element = XML(xml)
        self.assertEqual(element.tag,
                                "{urn:ietf:params:xml:ns:xmpp-tls}starttls")
        self.server.write(PROCEED)
        self.server.starttls(self.server.sock,
                            keyfile = os.path.join(DATA_DIR, "server-key.pem"),
                            certfile = os.path.join(DATA_DIR, "server.pem"),
                            server_side = True,
                            ca_certs = os.path.join(DATA_DIR, "ca.pem"),
                                )
        stream_start = self.wait(expect = re.compile(
                                    br"(<stream:stream[^>]*>)"))
        self.assertIsNotNone(stream_start)
        self.assertTrue(self.stream.tls_established)
        self.stream.disconnect()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(EMPTY_FEATURES)
        self.server.write(b"</stream:stream>")
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    TLSConnectingEvent, TLSConnectedEvent, StreamRestartedEvent,
                    GotFeaturesEvent, DisconnectedEvent])

    def test_enabled_required(self):
        """Test TLS enabled in settings, and required on the server."""
        self.start_server()
        settings = XMPPSettings({
                        u"starttls": True,
                        u"tls_cacert_file": os.path.join(DATA_DIR, "ca.pem"),
                                })
        handler = EventRecorder()
        handlers = [StreamTLSHandler(settings), handler]
        self.stream = StreamBase(u"jabber:client", None, handlers, settings)
        self.start_transport(handlers)
        self.stream.initiate(self.transport, to = "server.example.org")
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(TLS_REQUIRED_FEATURES)
        xml = self.wait(expect = re.compile(br".*(<starttls.*/>)"))
        self.assertIsNotNone(xml)
        element = XML(xml)
        self.assertEqual(element.tag,
                                "{urn:ietf:params:xml:ns:xmpp-tls}starttls")
        self.server.write(PROCEED)
        self.server.starttls(self.server.sock,
                            keyfile = os.path.join(DATA_DIR, "server-key.pem"),
                            certfile = os.path.join(DATA_DIR, "server.pem"),
                            server_side = True,
                            ca_certs = os.path.join(DATA_DIR, "ca.pem"),
                                )
        stream_start = self.wait(expect = re.compile(
                                                    br"(<stream:stream[^>]*>)"))
        self.assertIsNotNone(stream_start)
        self.assertTrue(self.stream.tls_established)
        self.stream.disconnect()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(EMPTY_FEATURES)
        self.server.write(b"</stream:stream>")
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    TLSConnectingEvent, TLSConnectedEvent, StreamRestartedEvent,
                    GotFeaturesEvent, DisconnectedEvent])

    def test_enabled_missing(self):
        """Test TLS enabled in settings, and missing on the server."""
        self.start_server()
        settings = XMPPSettings({
                        u"starttls": True,
                        u"tls_cacert_file": os.path.join(DATA_DIR, "ca.pem"),
                                })
        handler = EventRecorder()
        handlers = [StreamTLSHandler(settings), handler]
        self.stream = StreamBase(u"jabber:client", None, handlers, settings)
        self.start_transport(handlers)
        self.stream.initiate(self.transport, to = "server.example.org")
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(EMPTY_FEATURES)
        self.server.write(b"</stream:stream>")
        self.wait(expect = re.compile(br".*(</stream:stream>)"))
        self.assertFalse(self.stream.tls_established)
        self.stream.disconnect()
        self.server.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    DisconnectedEvent])

    def test_required_missing(self):
        """Test TLS required in settings, and missing on the server."""
        self.start_server()
        settings = XMPPSettings({
                        u"starttls": True,
                        u"tls_require": True,
                        u"tls_cacert_file": os.path.join(DATA_DIR, "ca.pem"),
                                })
        handler = EventRecorder()
        handlers = [StreamTLSHandler(settings), handler]
        self.stream = StreamBase(u"jabber:client", None, handlers, settings)
        self.start_transport(handlers)
        self.stream.initiate(self.transport, to = "server.example.org")
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(EMPTY_FEATURES)
        self.server.write(b"</stream:stream>")
        with self.assertRaises(TLSNegotiationFailed):
            self.wait()
        self.server.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    DisconnectedEvent])


# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
