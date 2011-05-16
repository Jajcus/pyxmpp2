#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.iq import Iq
from pyxmpp2.jid import JID
from pyxmpp2.stanzapayload import XMLPayload
from pyxmpp2.xmppserializer import serialize

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

class TestIq(unittest.TestCase):
    def check_iq1(self, iq):
        self.assertEqual(iq.from_jid, JID("source@example.com/res"))
        self.assertEqual(iq.to_jid, JID("dest@example.com"))
        self.assertEqual(iq.stanza_type, "get")
        self.assertEqual(iq.stanza_id, "1")
        payload = iq.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_namespace, 
                                        "http://pyxmpp.jajcus.net/xmlns/test")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag, 
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")

    def check_iq2(self, iq):
        self.assertEqual(iq.to_jid, JID("source@example.com/res"))
        self.assertEqual(iq.from_jid, JID("dest@example.com"))
        self.assertEqual(iq.stanza_type, "result")
        self.assertEqual(iq.stanza_id, "1")
        payload = iq.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_namespace, 
                                        "http://pyxmpp.jajcus.net/xmlns/test")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag, 
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")

    def check_iq3(self, iq):
        self.assertEqual(iq.from_jid, JID("source@example.com/res"))
        self.assertEqual(iq.to_jid, JID("dest@example.com"))
        self.assertEqual(iq.stanza_type, "set")
        self.assertEqual(iq.stanza_id, "2")
        payload = iq.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_namespace, 
                                        "http://pyxmpp.jajcus.net/xmlns/test")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag, 
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")

    def check_iq4(self, iq):
        self.assertEqual(iq.to_jid, JID("source@example.com/res"))
        self.assertEqual(iq.from_jid, JID("dest@example.com"))
        self.assertEqual(iq.stanza_type, "result")
        self.assertEqual(iq.stanza_id, "2")
        payload = iq.get_all_payload()
        self.assertFalse(payload)

    def test_iq_get_from_xml(self):
        iq = Iq(XML(IQ1))
        self.check_iq1(iq)

    def test_iq_result_full_from_xml(self):
        iq = Iq(XML(IQ2))
        self.check_iq2(iq)

    def test_iq_set_from_xml(self):
        iq = Iq(XML(IQ3))
        self.check_iq3(iq)

    def test_iq_result_empty_from_xml(self):
        iq = Iq(XML(IQ4))
        self.check_iq4(iq)

    def test_iq_get(self):
        iq = Iq( from_jid = JID("source@example.com/res"),
                to_jid = JID("dest@example.com"),
                stanza_type = "get",
                stanza_id = 1)
        payload = Element("{http://pyxmpp.jajcus.net/xmlns/test}t")
        SubElement(payload, "{http://pyxmpp.jajcus.net/xmlns/test}abc")
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
        payload = Element("{http://pyxmpp.jajcus.net/xmlns/test}t")
        SubElement(payload, "{http://pyxmpp.jajcus.net/xmlns/test}abc")
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
        payload = Element("{http://pyxmpp.jajcus.net/xmlns/test}t")
        SubElement(payload, "{http://pyxmpp.jajcus.net/xmlns/test}abc")
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
        iq = Iq(XML(IQ1))
        iq2 = iq.make_result_response()
        payload = Element("{http://pyxmpp.jajcus.net/xmlns/test}t")
        SubElement(payload, "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        payload = XMLPayload(payload)
        iq2.add_payload(payload)
        self.check_iq2(iq2)

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestIq))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
