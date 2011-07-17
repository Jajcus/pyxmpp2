#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import time
import re
import base64
import os

import pyxmpp2.etree

if "PYXMPP2_ETREE" not in os.environ:
    # one of tests fails when xml.etree.ElementTree is used
    try:
        import xml.etree.cElementTree
        pyxmpp2.etree.ElementTree = xml.etree.cElementTree
    except ImportError:
        pass

from pyxmpp2.etree import ElementTree

from pyxmpp2.streambase import StreamBase
from pyxmpp2.streamsasl import StreamSASLHandler
from pyxmpp2.streamevents import *
from pyxmpp2.exceptions import SASLAuthenticationFailed
from pyxmpp2.jid import JID
from pyxmpp2.settings import XMPPSettings

from pyxmpp2.interfaces import EventHandler, event_handler

from pyxmpp2.test._util import EventRecorder
from pyxmpp2.test._util import InitiatorSelectTestCase
from pyxmpp2.test._util import InitiatorPollTestMixIn, InitiatorThreadedTestMixIn
from pyxmpp2.test._util import ReceiverSelectTestCase
from pyxmpp2.test._util import ReceiverPollTestMixIn, ReceiverThreadedTestMixIn


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
        xml = self.wait(expect = re.compile(r".*(<auth.*</auth>)"))
        self.assertIsNotNone(xml)
        element = ElementTree.XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}auth")
        mech = element.get("mechanism")
        self.assertEqual(mech, "PLAIN")
        data = element.text.decode("base64")
        self.assertEqual(data, b"\000user\000secret")
        self.server.rdata = b""
        self.server.write(b"<success xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>")
        stream_start = self.wait(expect = re.compile(r"(<stream:stream[^>]*>)"))
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
        xml = self.wait(expect = re.compile(r".*(<auth.*</auth>)"))
        self.assertIsNotNone(xml)
        element = ElementTree.XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}auth")
        mech = element.get("mechanism")
        self.assertEqual(mech, "PLAIN")
        data = element.text.decode("base64")
        self.assertNotEqual(data, b"\000user\000secret")
        self.server.write(b"""<failure xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>
<not-authorized/></failure>""")
        with self.assertRaises(SASLAuthenticationFailed):
            self.wait()
        self.assertFalse(self.stream.authenticated)
        self.server.disconnect()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [ConnectingEvent,
                    ConnectedEvent, StreamConnectedEvent, GotFeaturesEvent])
 
class TestReceiver(ReceiverSelectTestCase):
    def test_auth(self):
        handler = EventRecorder()
        self.start_transport([handler])
        settings = XMPPSettings({
                                u"user_passwords": {
                                        u"user": u"secret",
                                    },
                                })
        self.stream = StreamBase(u"jabber:client", None,
                            [StreamSASLHandler(settings), handler], settings)
        self.stream.receive(self.transport, self.addr[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        xml = self.wait(expect = re.compile(
                                r".*<stream:features>(.*)</stream:features>"))
        self.assertIsNotNone(xml)
        element = ElementTree.XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")
        self.assertEqual(element[0].tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[0].text, "DIGEST-MD5")
        self.assertEqual(element[1].tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[1].text, "PLAIN")
        self.client.write(PLAIN_AUTH.format(
                                    base64.b64encode(b"\000user\000secret")))
        xml = self.wait(expect = re.compile(r".*(<success.*>)"))
        self.assertIsNotNone(xml)
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        xml = self.wait(expect = re.compile(r".*(<stream:stream.*>)"))
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
                                })
        self.stream = StreamBase(u"jabber:client", None,
                            [StreamSASLHandler(settings), handler], settings)
        self.stream.receive(self.transport, self.addr[0])
        self.client.write(C2S_CLIENT_STREAM_HEAD)
        xml = self.wait(expect = re.compile(
                                r".*<stream:features>(.*)</stream:features>"))
        self.assertIsNotNone(xml)
        element = ElementTree.XML(xml)
        self.assertEqual(element.tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms")
        self.assertEqual(element[0].tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[0].text, "DIGEST-MD5")
        self.assertEqual(element[1].tag, "{urn:ietf:params:xml:ns:xmpp-sasl}mechanism")
        self.assertEqual(element[1].text, "PLAIN")
        self.client.write(PLAIN_AUTH.format(
                                    base64.b64encode(b"\000user\000bad")))
        with self.assertRaises(SASLAuthenticationFailed):
            self.wait()
        self.client.write(b"</stream:stream>")
        self.client.disconnect()
        self.wait()
        event_classes = [e.__class__ for e in handler.events_received]
        self.assertEqual(event_classes, [StreamConnectedEvent, DisconnectedEvent])
 
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
