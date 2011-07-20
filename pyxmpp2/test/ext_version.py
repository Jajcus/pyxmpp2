#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest
import platform

from pyxmpp2.etree import ElementTree

import pyxmpp2.version
from pyxmpp2.iq import Iq
from pyxmpp2.jid import JID
from pyxmpp2.stanzaprocessor import StanzaProcessor
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.stanzapayload import XMLPayload

from pyxmpp2.ext.version import VersionPayload, VersionProvider
from pyxmpp2.ext.version import request_software_version


IQ1 = '''<iq type="get" id="1" xmlns="jabber:client">
<query xmlns="jabber:iq:version"/>
</iq>'''

IQ2 = '''<iq type="response" id="1" xmlns="jabber:client">
<query xmlns="jabber:iq:version">
  <name>NAME</name>
  <version>VERSION</version>
  <os>OS</os>
</query>
</iq>'''

class TestVersionPayload(unittest.TestCase):
    def test_parse_empty(self):
        element = ElementTree.XML(IQ1)
        payload = VersionPayload.from_xml(element[0])
        self.assertIsNone(payload.name)
        self.assertIsNone(payload.version)
        self.assertIsNone(payload.os_name)

    def test_parse_full(self):
        element = ElementTree.XML(IQ2)
        payload = VersionPayload.from_xml(element[0])
        self.assertEqual(payload.name, 'NAME')
        self.assertEqual(payload.version, 'VERSION')
        self.assertEqual(payload.os_name, 'OS')

    def test_build_empty(self):
        payload = VersionPayload()
        self.assertIsNone(payload.name)
        self.assertIsNone(payload.version)
        self.assertIsNone(payload.os_name)
        element = payload.as_xml()
        self.assertEqual(element.tag, "{jabber:iq:version}query")
        self.assertEqual(len(element), 0)

class Processor(StanzaProcessor):
    def __init__(self, handlers):
        StanzaProcessor.__init__(self)
        self.setup_stanza_handlers(handlers, "post-auth")
        self.stanzas_sent = []
    def send(self, stanza):
        self.stanzas_sent.append(stanza)

class TestVersionProvider(unittest.TestCase):
    def test_defaults(self):
        provider = VersionProvider()
        processor = Processor([provider])
        stanza = Iq(ElementTree.XML(IQ1))
        processor.uplink_receive(stanza)
        self.assertEqual(len(processor.stanzas_sent), 1)
        response = processor.stanzas_sent[0]
        self.assertIsInstance(response, Iq)
        self.assertEqual(response.stanza_type, "result")
        payload = response.get_payload(VersionPayload)
        self.assertIsInstance(payload, VersionPayload)
        self.assertEqual(payload.name, "PyXMPP2")
        self.assertEqual(payload.version, pyxmpp2.version.version)
        expected = u" ".join((platform.system(), platform.release(),
                                                        platform.machine()))
        self.assertEqual(payload.os_name, expected)

    def test_custom(self):
        settings = XMPPSettings({
                        "software_name": "NAME",
                        "software_version": "VERSION",
                        "software_os": "OS",
                            })
        provider = VersionProvider(settings)
        processor = Processor([provider])
        stanza = Iq(ElementTree.XML(IQ1))
        processor.uplink_receive(stanza)
        self.assertEqual(len(processor.stanzas_sent), 1)
        response = processor.stanzas_sent[0]
        self.assertIsInstance(response, Iq)
        self.assertEqual(response.stanza_type, "result")
        payload = response.get_payload(VersionPayload)
        self.assertIsInstance(payload, VersionPayload)
        self.assertEqual(payload.name, "NAME")
        self.assertEqual(payload.version, "VERSION")
        self.assertEqual(payload.os_name, "OS")

    def test_bad_request(self):
        provider = VersionProvider()
        processor = Processor([provider])
        stanza = Iq(ElementTree.XML(IQ2))
        stanza.stanza_type = 'set'
        processor.uplink_receive(stanza)
        self.assertEqual(len(processor.stanzas_sent), 1)
        response = processor.stanzas_sent[0]
        self.assertIsInstance(response, Iq)
        self.assertEqual(response.stanza_type, "error")
        self.assertEqual(response.error.condition.tag,
                    "{urn:ietf:params:xml:ns:xmpp-stanzas}service-unavailable")

class TestVersionRequest(unittest.TestCase):
    def test_request(self):
        payload_received = []
        errors_received = []
        def callback(payload):
            payload_received.append(payload)
        def error_callback(stanza):
            errors_received.append(stanza)
        processor = Processor([])
        request_software_version(processor, JID("test@example.org"),
                                                callback, error_callback)
        self.assertEqual(len(processor.stanzas_sent), 1)
        request = processor.stanzas_sent[0]
        self.assertIsInstance(request, Iq)
        self.assertEqual(request.stanza_type, "get")
        payload = request.get_payload(VersionPayload)
        self.assertIsNone(payload.name)
        self.assertIsNone(payload.version)
        self.assertIsNone(payload.os_name)
        response = request.make_result_response()
        payload = XMLPayload(ElementTree.XML(IQ2)[0])
        response.set_payload(payload)
        processor.uplink_receive(response)
        self.assertEqual(len(processor.stanzas_sent), 1)
        self.assertEqual(len(payload_received), 1)
        self.assertEqual(len(errors_received), 0)
        payload = payload_received[0]
        self.assertEqual(payload.name, "NAME")
        self.assertEqual(payload.version, "VERSION")
        self.assertEqual(payload.os_name, "OS")

    def test_request_error(self):
        payload_received = []
        errors_received = []
        def callback(payload):
            payload_received.append(payload)
        def error_callback(stanza):
            errors_received.append(stanza)
        processor = Processor([])
        request_software_version(processor, JID("test@example.org"),
                                                callback, error_callback)
        self.assertEqual(len(processor.stanzas_sent), 1)
        request = processor.stanzas_sent[0]
        self.assertIsInstance(request, Iq)
        self.assertEqual(request.stanza_type, "get")
        payload = request.get_payload(VersionPayload)
        self.assertIsNone(payload.name)
        self.assertIsNone(payload.version)
        self.assertIsNone(payload.os_name)
        response = request.make_error_response(u'service-unavailable')
        processor.uplink_receive(response)
        self.assertEqual(len(processor.stanzas_sent), 1)
        self.assertEqual(len(payload_received), 0)
        self.assertEqual(len(errors_received), 1)
        received = errors_received[0]
        self.assertIsInstance(received, Iq)
        self.assertEqual(received.stanza_type, "error")

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
