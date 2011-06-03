#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest

from pyxmpp2.etree import ElementTree

from pyxmpp2.message import Message
from pyxmpp2.jid import JID
from pyxmpp2.stanzapayload import XMLPayload
from pyxmpp2.xmppserializer import serialize

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
    def check_message_full(self, m):
        self.assertEqual(m.from_jid, JID("source@example.com/res"))
        self.assertEqual(m.to_jid, JID("dest@example.com"))
        self.assertEqual(m.stanza_type, "normal")
        self.assertEqual(m.stanza_id, "1")
        self.assertEqual(m.subject, u"Subject")
        self.assertEqual(m.body, u"The body")
        self.assertEqual(m.thread, u"thread-id")
        payload = m.get_all_payload()
        self.assertTrue(payload)
        self.assertEqual(payload[0].xml_element_name, 
                            "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.assertTrue(len(payload[0].element) > 0)
        self.assertEqual(payload[0].element[0].tag, 
                                "{http://pyxmpp.jajcus.net/xmlns/test}abc")

    def check_message_empty(self, m, can_have_id):
        self.assertEqual(m.from_jid, None)
        self.assertEqual(m.to_jid, None)
        self.assertEqual(m.stanza_type, None)
        if can_have_id:
            self.assertFalse(m.stanza_id is None)
        else:
            self.assertFalse(m.stanza_id is not None)
        self.assertEqual(m.subject, None)
        self.assertEqual(m.body, None)
        self.assertEqual(m.thread, None)
        payload = m.get_all_payload()
        self.assertFalse(payload)

    def test_message_full_from_xml(self):
        m = Message(ElementTree.XML(MESSAGE1))
        self.check_message_full(m)

    def test_message_empty_from_xml(self):
        m = Message(ElementTree.XML(MESSAGE2))
        self.check_message_empty(m, False)

    def test_message_empty(self):
        m = Message()
        self.check_message_empty(m, True)
        xml = m.as_xml()
        self.check_message_empty( Message(xml), True )

    def test_message_full(self):
        m = Message(
                from_jid = JID("source@example.com/res"),
                to_jid = JID("dest@example.com"),
                stanza_type = "normal",
                stanza_id = u"1",
                subject = u"Subject",
                body = u"The body",
                thread = u"thread-id")
        payload = ElementTree.Element("{http://pyxmpp.jajcus.net/xmlns/test}payload")
        ElementTree.SubElement(payload, "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        payload = XMLPayload(payload)
        m.add_payload(payload)
        self.check_message_full( m )
        xml = m.as_xml()
        self.check_message_full( Message(xml) )

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestMessage))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
