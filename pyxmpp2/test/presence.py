#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest

from pyxmpp2.etree import ElementTree

from pyxmpp2.presence import Presence
from pyxmpp2.jid import JID
from pyxmpp2.stanzapayload import XMLPayload

PRESENCE1 = """
<presence xmlns="jabber:client" from='source@example.com/res'
                                            to='dest@example.com' id='1'>
<show>away</show>
<status>The Status</status>
<priority>10</priority>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</presence>"""

PRESENCE2 = """<presence xmlns="jabber:client"/>"""

PRESENCE3 = """<presence xmlns="jabber:client" from='source@example.com/res'
                                to='dest@example.com' type="subscribe" />"""

class TestPresence(unittest.TestCase):
    def check_presence_full(self, pres):
        self.assertEqual(pres.from_jid, JID("source@example.com/res"))
        self.assertEqual(pres.to_jid, JID("dest@example.com"))
        self.assertEqual(pres.stanza_type, None)
        self.assertEqual(pres.stanza_id, "1")
        self.assertEqual(pres.show, "away")
        self.assertEqual(pres.status, "The Status")
        self.assertEqual(pres.priority, 10)
        payload = pres.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_element_name,
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")

    def check_presence_empty(self, pres):
        self.assertEqual(pres.from_jid, None)
        self.assertEqual(pres.to_jid, None)
        self.assertEqual(pres.stanza_type, None)
        self.assertIsNone(pres.stanza_id)
        self.assertEqual(pres.show, None)
        self.assertEqual(pres.status, None)
        self.assertEqual(pres.priority, 0)
        payload = pres.get_all_payload()
        self.assertFalse(payload)

    def check_presence_subscribe(self, pres):
        self.assertEqual(pres.from_jid, JID("source@example.com/res"))
        self.assertEqual(pres.to_jid, JID("dest@example.com"))
        self.assertEqual(pres.stanza_type, "subscribe")
        self.assertEqual(pres.stanza_id, None)
        self.assertEqual(pres.show, None)
        self.assertEqual(pres.status, None)

    def test_presence_full_from_xml(self):
        pres = Presence(ElementTree.XML(PRESENCE1))
        self.check_presence_full(pres)

    def test_presence_empty_from_xml(self):
        pres = Presence(ElementTree.XML(PRESENCE2))
        self.check_presence_empty(pres)

    def test_presence_subscribe_from_xml(self):
        pres = Presence(ElementTree.XML(PRESENCE3))
        self.check_presence_subscribe(pres)

    def test_presence_empty(self):
        pres = Presence()
        self.check_presence_empty(pres)
        xml = pres.as_xml()
        self.check_presence_empty(Presence(xml))

    def test_presence_full(self):
        pres = Presence(
                from_jid = JID("source@example.com/res"),
                to_jid = JID("dest@example.com"),
                stanza_type = None,
                stanza_id = u"1",
                show = u"away",
                status = u"The Status",
                priority = 10)
        payload = ElementTree.Element(
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        ElementTree.SubElement(payload,
                                    "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        payload = XMLPayload(payload)
        pres.add_payload(payload)
        self.check_presence_full(pres)
        xml = pres.as_xml()
        self.check_presence_full(Presence(xml))

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
