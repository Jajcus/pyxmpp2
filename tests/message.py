#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import libxml2
from pyxmpp.message import Message
from pyxmpp.jid import JID

message1 = """
<message xmlns="jabber:client" from='source@example.com/res' to='dest@example.com' type='normal' id='1'>
<subject>Subject</subject>
<body>The body</body>
<thread>thread-id</thread>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</message>"""

message1_doc = libxml2.parseDoc(message1)
message1_node = message1_doc.getRootElement()

message2 = """<message xmlns="jabber:client"/>"""

message2_doc = libxml2.parseDoc(message2)
message2_node = message2_doc.getRootElement()

class TestMessage(unittest.TestCase):
    def check_message_full(self, m):
        self.failUnlessEqual(m.get_from(), JID("source@example.com/res"))
        self.failUnlessEqual(m.get_to(), JID("dest@example.com"))
        self.failUnlessEqual(m.get_type(), "normal")
        self.failUnlessEqual(m.get_id(), "1")
        self.failUnlessEqual(m.get_subject(), u"Subject")
        self.failUnlessEqual(m.get_body(), u"The body")
        self.failUnlessEqual(m.get_thread(), u"thread-id")
        nodes = m.xpath_eval("t:payload", {"t": "http://pyxmpp.jajcus.net/xmlns/test"})
        self.failUnless(nodes)
        self.failUnlessEqual(nodes[0].name, "payload")
        self.failUnless(nodes[0].children)
        self.failUnlessEqual(nodes[0].children.name, "abc")

    def check_message_empty(self, m):
        self.failUnlessEqual(m.get_from(), None)
        self.failUnlessEqual(m.get_to(), None)
        self.failUnlessEqual(m.get_type(), None)
        self.failUnlessEqual(m.get_id(), None)
        self.failUnlessEqual(m.get_subject(), None)
        self.failUnlessEqual(m.get_body(), None)
        self.failUnlessEqual(m.get_thread(), None)
        nodes = m.xpath_eval("t:payload",{"t":"http://pyxmpp.jajcus.net/xmlns/test"})
        self.failIf(nodes)

    def test_message_full_from_xml(self):
        m = Message(message1_node)
        self.check_message_full(m)

    def test_message_empty_from_xml(self):
        m = Message(message2_node)
        self.check_message_empty(m)

    def test_message_empty(self):
        m = Message()
        self.check_message_empty(m)
        node, doc = self.stanza_to_xml(m)
        self.check_message_empty( Message(node) )
        node, doc = self.xml_to_xml(doc)
        self.check_message_empty( Message(node) )

    def test_message_full(self):
        m = Message(
                from_jid = JID("source@example.com/res"),
                to_jid = JID("dest@example.com"),
                stanza_type = "normal",
                stanza_id = u"1",
                subject = u"Subject",
                body = u"The body",
                thread = u"thread-id")
        n = m.xmlnode.newChild(None, "payload", None)
        ns = n.newNs("http://pyxmpp.jajcus.net/xmlns/test", "t")
        n.setNs(ns)
        n.newChild(ns, "abc", None)
        self.check_message_full( m )
        node, doc = self.stanza_to_xml(m)
        self.check_message_full( Message(node) )
        xml = self.xml_to_xml(doc)
        self.check_message_full( Message(node) )

    def stanza_to_xml(self, stanza):
        d = libxml2.newDoc("1.0")
        r = d.newChild(None, "root", None)
        ns = r.newNs("jabber:server", None)
        r.setNs(ns)
        d.setRootElement(r)
        xml = stanza.xmlnode.docCopyNode(d, 1)
        r.addChild(xml)
        return xml,d

    def xml_to_xml(self, xml):
        d = libxml2.parseDoc(xml.serialize())
        r = d.getRootElement()
        xml = r.children
        return xml, d

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestMessage))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
