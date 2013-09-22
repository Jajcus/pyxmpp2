#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest
import re
import base64
import binascii
import os

import pyxmpp2.etree

if "PYXMPP2_ETREE" not in os.environ:
    # one of tests fails when xml.etree.ElementTree is used
    try:
        from xml.etree import cElementTree
        pyxmpp2.etree.ElementTree = cElementTree
    except ImportError:
        pass

from pyxmpp2.etree import ElementTree

from pyxmpp2.streambase import StreamBase
from pyxmpp2.streamsasl import StreamSASLHandler
from pyxmpp2.streamevents import * # pylint: disable=W0614,W0401
from pyxmpp2.exceptions import SASLAuthenticationFailed
from pyxmpp2.settings import XMPPSettings

from pyxmpp2.test._util import EventRecorder
from pyxmpp2.test._util import InitiatorSelectTestCase
from pyxmpp2.test._util import ReceiverSelectTestCase

C2S_SERVER_STREAM_HEAD = (b'<stream:stream version="1.0" from="127.0.0.1"'
                            b' xmlns:stream="http://etherx.jabber.org/streams"'
                            b' xmlns="jabber:client">')
C2S_CLIENT_STREAM_HEAD = (b'<stream:stream version="1.0" to="127.0.0.1"'
                            b' xmlns:stream="http://etherx.jabber.org/streams"'
                            b' xmlns="jabber:client">')

AUTH_FEATURES = b"""<stream:features>
     <mechanisms xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>
        <mechanism>PLAIN</mechanism>
     </mechanisms>
</stream:features>"""

BIND_FEATURES = b"""<stream:features>
     <bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'/>
</stream:features>"""

PLAIN_AUTH = ("<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl'"
                                            " mechanism='PLAIN'>{0}</auth>")

STREAM_TAIL = b'</stream:stream>'

PARSE_ERROR_RESPONSE = (b'<stream:error><xml-not-well-formed'
                    b'  xmlns="urn:ietf:params:xml:ns:xmpp-streams"/>'
                                        b'</stream:error></stream:stream>')

TIMEOUT = 1.0 # seconds

class TestInitiator(InitiatorSelectTestCase):
    def test_auth(self):
        handler = EventRecorder()
        settings = XMPPSettings({
                                u"username": u"user",
                                u"password": u"secret",
                                })
        self.stream = StreamBase(u"jabber:client", None,
                            [StreamSASLHandler(settings), handler], settings)
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(AUTH_FEATURES)
        xml = self.wait(expect = re.compile(br".*(<auth.*</auth>)"))
        self.assertIsNotNone(xml)
        element = ElementTree.XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}auth")
        mech = element.get("mechanism")
        self.assertEqual(mech, "PLAIN")
        data = binascii.a2b_base64(element.text.encode("utf-8"))
        self.assertEqual(data, b"\000user\000secret")
        self.server.rdata = b""
        self.server.write(
                        b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
        stream_start = self.wait(expect = re.compile(
                                                br"(<stream:stream[^>]*>)"))
        self.assertIsNotNone(stream_start)
        self.assertTrue(self.stream.authenticated)
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(BIND_FEATURES)
        self.server.write(b"</stream:stream>")
        self.server.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                    StreamConnectedEvent, GotFeaturesEvent,
                    AuthenticatedEvent, StreamRestartedEvent, GotFeaturesEvent,
                    DisconnectedEvent])

    def test_auth_fail(self):
        handler = EventRecorder()
        settings = XMPPSettings({
                                u"username": u"user",
                                u"password": u"bad",
                                })
        self.stream = StreamBase(u"jabber:client", None,
                            [StreamSASLHandler(settings), handler], settings)
        self.start_transport([handler])
        self.stream.initiate(self.transport)
        self.connect_transport()
        self.server.write(C2S_SERVER_STREAM_HEAD)
        self.server.write(AUTH_FEATURES)
        xml = self.wait(expect = re.compile(br".*(<auth.*</auth>)"))
        self.assertIsNotNone(xml)
        element = ElementTree.XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}auth")
        mech = element.get("mechanism")
        self.assertEqual(mech, "PLAIN")
        data = binascii.a2b_base64(element.text.encode("utf-8"))
        self.assertNotEqual(data, b"\000user\000secret")
        self.server.write(b"""<failure xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>
<not-authorized/></failure>""")
        with self.assertRaises(SASLAuthenticationFailed):
            self.wait()
        self.assertFalse(self.stream.authenticated)
        self.server.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent, ConnectedEvent,
                    StreamConnectedEvent, GotFeaturesEvent, DisconnectedEvent])

class TestReceiver(ReceiverSelectTestCase):
    def test_auth(self):
        handler = EventRecorder()
        self.start_transport([handler])
        settings = XMPPSettings({
                                u"user_passwords": {
                                        u"user": u"secret",
                                    },
                                u"sasl_mechanisms": ["SCRAM-SHA-1", "PLAIN"],
                                })
        self.stream = StreamBase(u"jabber:client", None,
                            [StreamSASLHandler(settings), handler], settings)
        self.stream.receive(self.transport, self.addr[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        xml = self.wait(expect = re.compile(
                                br".*<stream:features>(.*)</stream:features>"))
        self.assertIsNotNone(xml)
        element = ElementTree.XML(xml)
        self.assertEqual(element.tag,
                                "{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")
        self.assertEqual(element[0].tag,
                                "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[0].text, "SCRAM-SHA-1")
        self.assertEqual(element[1].tag,
                                "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[1].text, "PLAIN")
        response = base64.standard_b64encode(b"\000user\000secret")
        self.client.write(PLAIN_AUTH.format(response.decode("utf-8"))
                                                    .encode("utf-8"))
        xml = self.wait(expect = re.compile(br".*(<success.*>)"))
        self.assertIsNotNone(xml)
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        xml = self.wait(expect = re.compile(br".*(<stream:stream.*>)"))
        self.assertIsNotNone(xml)
        self.assertTrue(self.stream.peer_authenticated)
        self.client.write(b"</stream:stream>")
        self.client.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [
                                StreamConnectedEvent, AuthenticatedEvent,
                                StreamRestartedEvent, DisconnectedEvent])

    def test_auth_fail(self):
        handler = EventRecorder()
        self.start_transport([handler])
        settings = XMPPSettings({
                                u"user_passwords": {
                                        u"user": u"secret",
                                    },
                                u"sasl_mechanisms": ["SCRAM-SHA-1", "PLAIN"],
                                })
        self.stream = StreamBase(u"jabber:client", None,
                            [StreamSASLHandler(settings), handler], settings)
        self.stream.receive(self.transport, self.addr[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        xml = self.wait(expect = re.compile(
                                br".*<stream:features>(.*)</stream:features>"))
        self.assertIsNotNone(xml)
        element = ElementTree.XML(xml)
        self.assertEqual(element.tag,
                                "{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")
        self.assertEqual(element[0].tag,
                                "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[0].text, "SCRAM-SHA-1")
        self.assertEqual(element[1].tag,
                                "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[1].text, "PLAIN")
        response = base64.standard_b64encode(b"\000user\000bad")
        self.client.write(PLAIN_AUTH.format(response.decode("us-ascii"))
                                                            .encode("utf-8"))
        with self.assertRaises(SASLAuthenticationFailed):
            self.wait()
        self.client.write(b"</stream:stream>")
        self.client.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [StreamConnectedEvent,
                                                            DisconnectedEvent])

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
