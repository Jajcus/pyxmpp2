#!/usr/bin/python -u
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest

import re

from pyxmpp2.etree import ElementTree

from pyxmpp2.interfaces import StanzaPayload
from pyxmpp2.interfaces import payload_element_name

from pyxmpp2.stanzapayload import XMLPayload

from pyxmpp2.stanza import Stanza
from pyxmpp2.jid import JID

from pyxmpp2.utils import xml_elements_equal


STANZA0 = "<presence xmlns='jabber:client' />"
STANZA1 = "<presence xmlns='jabber:server'><status>STATUS</status></presence>"
STANZA2 = "<message xmlns='jabber:client' />"
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

STANZA6 = """
<iq from='a@b.c/d' to='e@f.g/h' id='666' type='get' xmlns='jabber:client'>
    <element xmlns='http://pyxmpp.jajcus.net/test/ns' />
</iq>
"""
STANZA7 = """
<iq from='a@b.c/d' to='e@f.g/h' id='666' type='get' xmlns='jabber:client'>
    <element xmlns='http://pyxmpp.jajcus.net/test/ns'><data>Test</data></element>
</iq>
"""


@payload_element_name(u"{http://pyxmpp.jajcus.net/test/ns}element")
class TestPayload(StanzaPayload):
    def __init__(self, data = None):
        self.data = data

    @classmethod
    def from_xml(cls, element):
        data = None
        for child in element:
            if child.tag == u"{http://pyxmpp.jajcus.net/test/ns}data":
                data = child.text
        return cls(data)

    def as_xml(self):
        element = ElementTree.Element(
                                u"{http://pyxmpp.jajcus.net/test/ns}element")
        if self.data:
            ElementTree.SubElement(element,
                    u"{http://pyxmpp.jajcus.net/test/ns}data").text = self.data
        return element

class TestStanza(unittest.TestCase):
    def test_stanza_from_empty_element(self):
        stanza0 = Stanza(ElementTree.XML(STANZA0))
        self.assertEqual(stanza0.element_name, "presence")
        self.assertEqual(stanza0.from_jid, None)
        self.assertEqual(stanza0.to_jid, None)
        self.assertEqual(stanza0.stanza_type, None)
        self.assertEqual(stanza0.stanza_id, None)
        stanza1 = Stanza(ElementTree.XML(STANZA1))
        self.assertEqual(stanza1.element_name, "presence")
        self.assertEqual(stanza1.from_jid, None)
        self.assertEqual(stanza1.to_jid, None)
        self.assertEqual(stanza1.stanza_type, None)
        self.assertEqual(stanza1.stanza_id, None)
        stanza2 = Stanza(ElementTree.XML(STANZA2))
        self.assertEqual(stanza2.element_name, "message")
        self.assertEqual(stanza2.from_jid, None)
        self.assertEqual(stanza2.to_jid, None)
        self.assertEqual(stanza2.stanza_type, None)
        self.assertEqual(stanza2.stanza_id, None)
    def test_stanza_attributes(self):
        stanza3 = Stanza(ElementTree.XML(STANZA3))
        self.assertEqual(stanza3.element_name, u"presence")
        self.assertEqual(stanza3.from_jid, JID(u"a@b.c/d"))
        self.assertEqual(stanza3.to_jid, JID(u"e@f.g/h"))
        self.assertEqual(stanza3.stanza_type, u"unavailable")
        self.assertEqual(stanza3.stanza_id, u'666')
    def test_stanza_build(self):
        stanza = Stanza("presence", from_jid = JID('a@b.c/d'),
                            to_jid = JID('e@f.g/h'), stanza_id = '666',
                            stanza_type = 'unavailable')
        self.assertTrue(xml_elements_equal(stanza.as_xml(),
                                                    ElementTree.XML(STANZA3)))
    def test_serialize1(self):
        for xml in (STANZA0, STANZA1, STANZA2, STANZA3, STANZA4, STANZA5):
            stanza = Stanza(ElementTree.XML(xml))
            element1 = ElementTree.XML(re.sub(r" xmlns='jabber:[^'\":]*'",
                                                                    "", xml))
            element2 = ElementTree.XML(stanza.serialize())
            self.assertTrue(xml_elements_equal(element1, element2, True))
    def test_serialize2(self):
        stanza = Stanza("presence", from_jid = JID('a@b.c/d'),
                            to_jid = JID('e@f.g/h'), stanza_id = '666',
                            stanza_type = 'unavailable')
        xml = stanza.serialize()
        self.assertTrue(xml_elements_equal(ElementTree.XML(xml),
            ElementTree.XML(STANZA3.replace(" xmlns='jabber:client'",""))))

    def test_stanza_as_xml(self):
        # STANZA1 and STANZA2 won't match as have no namespace
        for xml in (STANZA0, STANZA3, STANZA4, STANZA5):
            stanza = Stanza(ElementTree.XML(xml))
            self.assertTrue(xml_elements_equal(stanza.as_xml(),
                                                ElementTree.XML(xml), True))
    def test_stanza_get_xml(self):
        for xml in (STANZA0, STANZA1, STANZA2, STANZA3, STANZA4, STANZA5):
            element = ElementTree.XML(xml)
            stanza = Stanza(element)
            self.assertTrue(stanza.get_xml() is element)
    def test_stanza_payload(self):
        stanza5 = Stanza(ElementTree.XML(STANZA5))
        payload = stanza5.get_all_payload()
        self.assertEqual(len(payload), 1)
        payload = payload[0]
        self.assertIsInstance(payload, StanzaPayload)
        self.assertIsInstance(payload, XMLPayload)
        self.assertEqual(payload.xml_element_name, "{jabber:iq:version}query")
        self.assertTrue(xml_elements_equal(
                            ElementTree.XML(STANZA5)[0], payload.element))

    def test_stanza_get_custom_payload(self):
        stanza6 = Stanza(ElementTree.XML(STANZA6))
        payload = stanza6.get_payload(TestPayload)
        self.assertIsInstance(payload, TestPayload)
        self.assertIsNone(payload.data) # pylint: disable=E1103
        self.assertTrue(xml_elements_equal(ElementTree.XML(STANZA6)[0],
                                                            payload.as_xml()))

    def test_stanza_set_custom_payload(self):
        stanza7 = Stanza("iq", from_jid = JID('a@b.c/d'),
                            to_jid = JID('e@f.g/h'), stanza_id = '666',
                            stanza_type='get')
        payload = TestPayload(data = u"Test")
        stanza7.set_payload(payload)
        payload1 = stanza7.get_payload(TestPayload)
        self.assertTrue(payload1 is payload)
        self.assertTrue(xml_elements_equal(ElementTree.XML(STANZA7),
                                                    stanza7.as_xml(), True))

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
