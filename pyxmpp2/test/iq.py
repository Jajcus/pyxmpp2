#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest

from pyxmpp2.etree import ElementTree

from pyxmpp2.iq import Iq
from pyxmpp2.jid import JID
from pyxmpp2.stanzapayload import XMLPayload
from pyxmpp2.error import StanzaErrorElement

IQ1 = """
<iq xmlns="jabber:client" from='source@example.com/res'
                                to='dest@example.com' type='get' id='1'>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</iq>"""

IQ2 = """
<iq xmlns="jabber:client" to='source@example.com/res'
                                from='dest@example.com' type='result' id='1'>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</iq>"""

IQ3 = """
<iq xmlns="jabber:client" from='source@example.com/res'
                                to='dest@example.com' type='set' id='2'>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</iq>"""

IQ4 = """
<iq xmlns="jabber:client" to='source@example.com/res'
                                from='dest@example.com' type='result' id='2'>
</iq>"""

IQ5 = """
<iq xmlns="jabber:client" to='source@example.com/res'
                                from='dest@example.com' type='error' id='1'>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
<error type="modify"><bad-request xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>
</iq>"""


class TestIq(unittest.TestCase):
    def check_iq1(self, iq):
        self.assertEqual(iq.from_jid, JID("source@example.com/res"))
        self.assertEqual(iq.to_jid, JID("dest@example.com"))
        self.assertEqual(iq.stanza_type, "get")
        self.assertEqual(iq.stanza_id, "1")
        payload = iq.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_element_name,
                            "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        self.assertFalse(iq.error)

    def check_iq2(self, iq):
        self.assertEqual(iq.to_jid, JID("source@example.com/res"))
        self.assertEqual(iq.from_jid, JID("dest@example.com"))
        self.assertEqual(iq.stanza_type, "result")
        self.assertEqual(iq.stanza_id, "1")
        payload = iq.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_element_name,
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        self.assertFalse(iq.error)

    def check_iq3(self, iq):
        self.assertEqual(iq.from_jid, JID("source@example.com/res"))
        self.assertEqual(iq.to_jid, JID("dest@example.com"))
        self.assertEqual(iq.stanza_type, "set")
        self.assertEqual(iq.stanza_id, "2")
        payload = iq.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_element_name,
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        self.assertFalse(iq.error)

    def check_iq4(self, iq):
        self.assertEqual(iq.to_jid, JID("source@example.com/res"))
        self.assertEqual(iq.from_jid, JID("dest@example.com"))
        self.assertEqual(iq.stanza_type, "result")
        self.assertEqual(iq.stanza_id, "2")
        payload = iq.get_all_payload()
        self.assertFalse(payload)
        self.assertFalse(iq.error)

    def check_iq5(self, iq):
        self.assertEqual(iq.to_jid, JID("source@example.com/res"))
        self.assertEqual(iq.from_jid, JID("dest@example.com"))
        self.assertEqual(iq.stanza_type, "error")
        self.assertEqual(iq.stanza_id, "1")
        payload = iq.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_element_name,
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        error = iq.error
        self.assertIsInstance(error, StanzaErrorElement)
        self.assertEqual(error.condition_name, "bad-request")

    def test_iq_get_from_xml(self):
        iq = Iq(ElementTree.XML(IQ1))
        self.check_iq1(iq)

    def test_iq_result_full_from_xml(self):
        iq = Iq(ElementTree.XML(IQ2))
        self.check_iq2(iq)

    def test_iq_set_from_xml(self):
        iq = Iq(ElementTree.XML(IQ3))
        self.check_iq3(iq)

    def test_iq_result_empty_from_xml(self):
        iq = Iq(ElementTree.XML(IQ4))
        self.check_iq4(iq)

    def test_iq_get(self):
        iq = Iq( from_jid = JID("source@example.com/res"),
                to_jid = JID("dest@example.com"),
                stanza_type = "get",
                stanza_id = 1)
        payload = ElementTree.Element(
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        ElementTree.SubElement(payload,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        payload = XMLPayload(payload)
        iq.add_payload(payload)
        self.check_iq1(iq)
        xml = iq.as_xml()
        self.check_iq1( Iq(xml) )

    def test_iq_result_full(self):
        iq = Iq( to_jid = JID("source@example.com/res"),
                from_jid = JID("dest@example.com"),
                stanza_type = "result",
                stanza_id = 1)
        payload = ElementTree.Element(
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        ElementTree.SubElement(payload,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        payload = XMLPayload(payload)
        iq.add_payload(payload)
        self.check_iq2(iq)
        xml = iq.as_xml()
        self.check_iq2( Iq(xml) )

    def test_iq_set(self):
        iq = Iq( from_jid = JID("source@example.com/res"),
                to_jid = JID("dest@example.com"),
                stanza_type = "set",
                stanza_id = 2)
        payload = ElementTree.Element(
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        ElementTree.SubElement(payload,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        payload = XMLPayload(payload)
        iq.add_payload(payload)
        self.check_iq3(iq)
        xml = iq.as_xml()
        self.check_iq3( Iq(xml) )

    def test_iq_result_empty(self):
        iq = Iq( to_jid = JID("source@example.com/res"),
                from_jid = JID("dest@example.com"),
                stanza_type = "result",
                stanza_id = 2)
        self.check_iq4(iq)
        xml = iq.as_xml()
        self.check_iq4( Iq(xml) )

    def test_iq_make_result_response(self):
        iq = Iq(ElementTree.XML(IQ1))
        iq2 = iq.make_result_response()
        payload = ElementTree.Element(
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        ElementTree.SubElement(payload,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        payload = XMLPayload(payload)
        iq2.add_payload(payload)
        self.check_iq2(iq2)

    def test_iq_make_error_response(self):
        iq = Iq(ElementTree.XML(IQ1))
        iq5 = iq.make_error_response(u"bad-request")
        self.check_iq5(iq5)
        xml = iq5.as_xml()
        self.check_iq5( Iq(xml) )

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
