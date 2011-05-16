#!/usr/bin/python -u
# -*- coding: UTF-8 -*-

import unittest
from xml.etree import ElementTree
from xml.etree.ElementTree import XML

from pyxmpp2.stanza import Stanza
from pyxmpp2.jid import JID

from pyxmpp2.utils import xml_elements_equal


STANZA0 = "<presence xmlns='jabber:client' />"
STANZA1 = "<presence />"
STANZA2 = "<message />"
STANZA3 = """
<presence from='a@b.c/d' to='e@f.g/h' id='666' type='unavailable' 
                                                xmlns='jabber:client'/>
"""
STANZA4 = """
<message from='a@b.c/d' to='e@f.g' id='666' type='chat' 
                                                    xmlns='jabber:client'>
        <subject>Subject</subject>
        <body>Body</body>
</message>
"""

STANZA5 = """
<iq from='a@b.c/d' to='e@f.g/h' id='666' type='get' xmlns='jabber:client'>
    <query xmlns='jabber:iq:version' />
</iq>
"""

class TestStanza(unittest.TestCase):
    def test_stanza_from_empty_element(self):
        stanza0 = Stanza(XML(STANZA0))
        self.assertEqual(stanza0.element_name, "presence")
        self.assertEqual(stanza0.from_jid, None)
        self.assertEqual(stanza0.to_jid, None)
        self.assertEqual(stanza0.stanza_type, None)
        self.assertEqual(stanza0.stanza_id, None)
        stanza1 = Stanza(XML(STANZA1))
        self.assertEqual(stanza1.element_name, "presence")
        self.assertEqual(stanza1.from_jid, None)
        self.assertEqual(stanza1.to_jid, None)
        self.assertEqual(stanza1.stanza_type, None)
        self.assertEqual(stanza1.stanza_id, None)
        stanza2 = Stanza(XML(STANZA2))
        self.assertEqual(stanza2.element_name, "message")
        self.assertEqual(stanza2.from_jid, None)
        self.assertEqual(stanza2.to_jid, None)
        self.assertEqual(stanza2.stanza_type, None)
        self.assertEqual(stanza2.stanza_id, None)
    def test_stanza_attributes(self):
        stanza3 = Stanza(XML(STANZA3))
        self.assertEqual(stanza3.element_name, u"presence")
        self.assertEqual(stanza3.from_jid, JID(u"a@b.c/d"))
        self.assertEqual(stanza3.to_jid, JID(u"e@f.g/h"))
        self.assertEqual(stanza3.stanza_type, u"unavailable")
        self.assertEqual(stanza3.stanza_id, u'666')
    def test_stanza_build(self):
        stanza = Stanza("presence", from_jid = JID('a@b.c/d'), 
                            to_jid = JID('e@f.g/h'), stanza_id = '666',
                            stanza_type = 'unavailable')
        self.assertTrue(xml_elements_equal(stanza.as_xml(), XML(STANZA3)))
    def test_serialize1(self):
        for xml in (STANZA0, STANZA1, STANZA2, STANZA3, STANZA4, STANZA5):
            stanza = Stanza(XML(xml))
            element1 = XML(xml.replace(" xmlns='jabber:client'",""))
            element2 = XML(stanza.serialize())
            self.assertTrue(xml_elements_equal(element1, element2, True))
    def test_serialize2(self):
        stanza = Stanza("presence", from_jid = JID('a@b.c/d'), 
                            to_jid = JID('e@f.g/h'), stanza_id = '666',
                            stanza_type = 'unavailable')
        xml = stanza.serialize()
        self.assertTrue(xml_elements_equal(XML(xml),
            XML(STANZA3.replace(" xmlns='jabber:client'",""))))

    def test_stanza_as_xml(self):
        # STANZA1 and STANZA2 won't match as have no namespace
        for xml in (STANZA0, STANZA3, STANZA4, STANZA5):
            stanza = Stanza(XML(xml))
            self.assertTrue(xml_elements_equal(stanza.as_xml(), XML(xml), True))
    def test_stanza_get_xml(self):
        for xml in (STANZA0, STANZA1, STANZA2, STANZA3, STANZA4, STANZA5):
            element = XML(xml)
            stanza = Stanza(element)
            self.assertTrue(stanza.get_xml() is element)
    def test_stanza_payload(self):
        from pyxmpp2.stanzapayload import StanzaPayload, XMLPayload
        stanza5 = Stanza(XML(STANZA5))
        payload = stanza5.get_all_payload()
        self.assertEqual(len(payload), 1)
        payload = payload[0]
        self.assertTrue(isinstance(payload, StanzaPayload))
        self.assertTrue(isinstance(payload, XMLPayload))
        self.assertEqual(payload.xml_namespace, "jabber:iq:version")
        self.assertTrue(xml_elements_equal(
                            XML(STANZA5)[0], payload.element))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestStanza))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
