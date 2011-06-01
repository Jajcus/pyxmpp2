#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import time
import re
import base64

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.streambase import StreamBase, XMPPEventHandler
from pyxmpp2.streamsasl import StreamSASLHandler
from pyxmpp2.streamevents import *
from pyxmpp2.exceptions import SASLAuthenticationFailed
from pyxmpp2.jid import JID
from pyxmpp2.settings import XMPPSettings

from test_util import NetworkTestCase

C2S_SERVER_STREAM_HEAD = '<stream:stream version="1.0" from="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'
C2S_CLIENT_STREAM_HEAD = '<stream:stream version="1.0" to="127.0.0.1" xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client">'

AUTH_FEATURES = """<stream:features>
     <mechanisms xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>
        <mechanism>PLAIN</mechanism>
     </mechanisms>
</stream:features>"""

BIND_FEATURES = """<stream:features>
     <bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'/>
</stream:features>"""

PLAIN_AUTH = "<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>{0}</auth>"

STREAM_TAIL = '</stream:stream>'
        
PARSE_ERROR_RESPONSE = ('<stream:error><xml-not-well-formed'
                    '  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/>'
                                        '</stream:error></stream:stream>')

TIMEOUT = 1.0 # seconds

class IgnoreEventHandler(XMPPEventHandler):
    def __init__(self):
        self.events_received = []
    def handle_xmpp_event(self, event):
        self.events_received.append(event)
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

    def test_auth(self):
        addr, port = self.start_server()
        handler = IgnoreEventHandler()
        settings = XMPPSettings({
                                u"username": u"user", 
                                u"password": u"secret",
                                })
        stream = StreamBase(u"jabber:client", [StreamSASLHandler(settings), handler], settings)
        stream.connect(addr, port)
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(AUTH_FEATURES)
        xml = self.loop(stream, timeout = 1, expect = re.compile(
                                           r".*(<auth.*</auth>)"))
        self.assertIsNotNone(xml)
        element = XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}auth")
        mech = element.get("mechanism")
        self.assertEqual(mech, "PLAIN")
        data = element.text.decode("base64")
        self.assertEqual(data, b"\000user\000secret")
        self.server.rdata = b""
        self.server.write(b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
        stream_start = self.loop(stream, timeout = 1, expect = re.compile(
                                                    r"(<stream:stream[^>]*>)"))
        self.assertIsNotNone(stream_start)
        self.assertTrue(stream.authenticated)
        stream.disconnect()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(BIND_FEATURES)
        self.server.write(b"</stream:stream>")
        self.loop(stream)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    AuthenticatedEvent, StreamConnectedEvent, GotFeaturesEvent, 
                    DisconnectedEvent])
 
    def test_auth_fail(self):
        addr, port = self.start_server()
        handler = IgnoreEventHandler()
        settings = XMPPSettings({
                                u"username": u"user", 
                                u"password": u"badsecret",
                                })
        stream = StreamBase(u"jabber:client", [StreamSASLHandler(settings), handler], settings)
        stream.connect(addr, port)
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(AUTH_FEATURES)
        xml = self.loop(stream, timeout = 1, expect = re.compile(
                                           r".*(<auth.*</auth>)"))
        self.assertIsNotNone(xml)
        element = XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}auth")
        mech = element.get("mechanism")
        self.assertEqual(mech, "PLAIN")
        data = element.text.decode("base64")
        self.assertNotEqual(data, b"\000user\000secret")
        self.server.write(b"""<failure xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>
<not-authorized/></failure>""")
        with self.assertRaises(SASLAuthenticationFailed):
            self.loop(stream)
        self.assertFalse(stream.authenticated)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ResolvingAddressEvent, ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent,
                    DisconnectedEvent])
 
class TestReceiver(NetworkTestCase):
    def loop(self, stream, timeout = TIMEOUT, expect = None):
        timeout = time.time() + timeout
        while stream.socket and time.time() < timeout:
            stream.loop_iter(0.1)
            if expect:
                match = expect.match(self.client.rdata)
                if match:
                    return match.group(1)

    def test_auth(self):
        sock = self.make_listening_socket()
        self.start_client(sock.getsockname())
        handler = IgnoreEventHandler()
        settings = XMPPSettings({
                                u"user_passwords": {
                                        u"user": u"secret",
                                    },
                                })
        stream = StreamBase(u"jabber:client", [StreamSASLHandler(settings), handler], settings)
        stream.accept(sock, sock.getsockname()[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        xml = self.loop(stream, timeout = 1, expect = re.compile(
            r".*<stream:features>(.*)</stream:features>"))
        self.assertIsNotNone(xml)
        element = XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")
        self.assertEqual(element[0].tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[0].text, "DIGEST-MD5")
        self.assertEqual(element[1].tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[1].text, "PLAIN")
        self.client.write(PLAIN_AUTH.format(
                                    base64.b64encode(b"\000user\000secret")))
        xml = self.loop(stream, timeout = 1, expect = re.compile(
                                        r".*(<success.*>)"))
        self.assertIsNotNone(xml)
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        xml = self.loop(stream, timeout = 1, expect = re.compile(
                                                    r".*(<stream:stream.*>)"))
        self.assertIsNotNone(xml)
        self.assertTrue(stream.peer_authenticated)
        stream.disconnect()
        self.client.write(b"</stream:stream>")
        self.loop(stream)
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectionAcceptedEvent,
                                StreamConnectedEvent, AuthenticatedEvent,
                                StreamConnectedEvent, DisconnectedEvent])
 
    def test_auth_fail(self):
        sock = self.make_listening_socket()
        self.start_client(sock.getsockname())
        handler = IgnoreEventHandler()
        settings = XMPPSettings({
                                u"user_passwords": {
                                        u"user": u"secret",
                                    },
                                })
        stream = StreamBase(u"jabber:client", [StreamSASLHandler(settings), handler], settings)
        stream.accept(sock, sock.getsockname()[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        xml = self.loop(stream, timeout = 1, expect = re.compile(
            r".*<stream:features>(.*)</stream:features>"))
        self.assertIsNotNone(xml)
        element = XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")
        self.assertEqual(element[0].tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[0].text, "DIGEST-MD5")
        self.assertEqual(element[1].tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[1].text, "PLAIN")
        self.client.write(PLAIN_AUTH.format(
                                    base64.b64encode(b"\000user\000bad")))
        with self.assertRaises(SASLAuthenticationFailed):
            self.loop(stream)
        self.client.write(b"</stream:stream>")
        self.loop(stream)
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
