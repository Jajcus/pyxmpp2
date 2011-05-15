#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.presence import Presence
from pyxmpp2.jid import JID
from pyxmpp2.utils import xml_elements_equal
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
    def check_presence_full(self, p):
        self.failUnlessEqual(p.from_jid, JID("source@example.com/res"))
        self.failUnlessEqual(p.to_jid, JID("dest@example.com"))
        self.failUnlessEqual(p.stanza_type, None)
        self.failUnlessEqual(p.stanza_id, "1")
        self.failUnlessEqual(p.show, "away")
        self.failUnlessEqual(p.status, "The Status")
        self.failUnlessEqual(p.priority, 10)
        payload = p.get_all_payload()
        self.failUnless(payload)
        self.failUnlessEqual(payload[0].xml_namespace, 
                                        "http://pyxmpp.jajcus.net/xmlns/test")
        self.failUnless(len(payload[0].element) > 0)
        self.failUnlessEqual(payload[0].element[0].tag, 
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")

    def check_presence_empty(self, p, can_have_id):
        self.failUnlessEqual(p.from_jid, None)
        self.failUnlessEqual(p.to_jid, None)
        self.failUnlessEqual(p.stanza_type, None)
        if can_have_id:
            self.failIf(p.stanza_id is None)
        else:
            self.failIf(p.stanza_id is not None)
        self.failUnlessEqual(p.show, None)
        self.failUnlessEqual(p.status, None)
        self.failUnlessEqual(p.priority, 0)
        payload = p.get_all_payload()
        self.failIf(payload)

    def check_presence_subscribe(self, p):
        self.failUnlessEqual(p.from_jid, JID("source@example.com/res"))
        self.failUnlessEqual(p.to_jid, JID("dest@example.com"))
        self.failUnlessEqual(p.stanza_type, "subscribe")
        self.failUnlessEqual(p.stanza_id, None)
        self.failUnlessEqual(p.show, None)
        self.failUnlessEqual(p.status, None)

    def test_presence_full_from_xml(self):
        p = Presence(XML(PRESENCE1))
        self.check_presence_full(p)

    def test_presence_empty_from_xml(self):
        p = Presence(XML(PRESENCE2))
        self.check_presence_empty(p, False)

    def test_presence_subscribe_from_xml(self):
        p = Presence(XML(PRESENCE3))
        self.check_presence_subscribe(p)

    def test_presence_empty(self):
        p = Presence()
        self.check_presence_empty(p, True)
        xml = p.as_xml()
        self.check_presence_empty(Presence(xml), True)

    def test_presence_full(self):
        p = Presence(
                from_jid = JID("source@example.com/res"),
                to_jid = JID("dest@example.com"),
                stanza_type = None,
                stanza_id = u"1",
                show = u"away",
                status = u"The Status",
                priority = 10)
        payload = Element("{http://pyxmpp.jajcus.net/xmlns/test}t")
        SubElement(payload, "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        payload = XMLPayload(payload)
        p.add_payload(payload)
        self.check_presence_full(p)
        xml = p.as_xml()
        self.check_presence_full( Presence(xml) )

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestPresence))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
