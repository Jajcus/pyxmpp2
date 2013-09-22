#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest

from pyxmpp2.etree import ElementTree

from pyxmpp2.message import Message
from pyxmpp2.jid import JID
from pyxmpp2.stanzapayload import XMLPayload

MESSAGE1 = """
<message xmlns="jabber:client" from='source@example.com/res'
                                to='dest@example.com' type='normal' id='1'>
<subject>Subject</subject>
<body>The body</body>
<thread>thread-id</thread>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</message>"""

MESSAGE2 = """<message xmlns="jabber:client"/>"""

class TestMessage(unittest.TestCase):
    def check_message_full(self, msg):
        self.assertEqual(msg.from_jid, JID("source@example.com/res"))
        self.assertEqual(msg.to_jid, JID("dest@example.com"))
        self.assertEqual(msg.stanza_type, "normal")
        self.assertEqual(msg.stanza_id, "1")
        self.assertEqual(msg.subject, u"Subject")
        self.assertEqual(msg.body, u"The body")
        self.assertEqual(msg.thread, u"thread-id")
        payload = msg.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_element_name,
                            "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")

    def check_message_empty(self, msg):
        self.assertEqual(msg.from_jid, None)
        self.assertEqual(msg.to_jid, None)
        self.assertEqual(msg.stanza_type, None)
        self.assertIsNone(msg.stanza_id)
        self.assertEqual(msg.subject, None)
        self.assertEqual(msg.body, None)
        self.assertEqual(msg.thread, None)
        payload = msg.get_all_payload()
        self.assertFalse(payload)

    def test_message_full_from_xml(self):
        msg = Message(ElementTree.XML(MESSAGE1))
        self.check_message_full(msg)

    def test_message_empty_from_xml(self):
        msg = Message(ElementTree.XML(MESSAGE2))
        self.check_message_empty(msg)

    def test_message_empty(self):
        msg = Message()
        self.check_message_empty(msg)
        xml = msg.as_xml()
        self.check_message_empty(Message(xml))

    def test_message_full(self):
        msg = Message(
                from_jid = JID("source@example.com/res"),
                to_jid = JID("dest@example.com"),
                stanza_type = "normal",
                stanza_id = u"1",
                subject = u"Subject",
                body = u"The body",
                thread = u"thread-id")
        payload = ElementTree.Element(
                            "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        ElementTree.SubElement(payload,
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        payload = XMLPayload(payload)
        msg.add_payload(payload)
        self.check_message_full(msg)
        xml = msg.as_xml()
        self.check_message_full(Message(xml))

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
