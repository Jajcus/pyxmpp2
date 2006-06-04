#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import libxml2
from pyxmpp.presence import Presence
from pyxmpp.jid import JID

presence1 = """
<presence xmlns="jabber:client" from='source@example.com/res' to='dest@example.com' id='1'>
<show>away</show>
<status>The Status</status>
<priority>10</priority>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</presence>"""
presence1_doc = libxml2.parseDoc(presence1)
presence1_node = presence1_doc.getRootElement()

presence2 = """<presence xmlns="jabber:client"/>"""
presence2_doc = libxml2.parseDoc(presence2)
presence2_node = presence2_doc.getRootElement()

presence3 = """<presence xmlns="jabber:client" from='source@example.com/res' to='dest@example.com' type="subscribe" />"""
presence3_doc = libxml2.parseDoc(presence3)
presence3_node = presence3_doc.getRootElement()

class TestPresence(unittest.TestCase):
    def check_presence_full(self, p):
        self.failUnlessEqual(p.get_from(), JID("source@example.com/res"))
        self.failUnlessEqual(p.get_to(), JID("dest@example.com"))
        self.failUnlessEqual(p.get_type(), None)
        self.failUnlessEqual(p.get_id(), "1")
        self.failUnlessEqual(p.get_show(), "away")
        self.failUnlessEqual(p.get_status(), "The Status")
        self.failUnlessEqual(p.get_priority(), 10)
        nodes = p.xpath_eval("t:payload", {"t": "http://pyxmpp.jajcus.net/xmlns/test"})
        self.failUnless(nodes)
        self.failUnlessEqual(nodes[0].name, "payload")
        self.failUnless(nodes[0].children)
        self.failUnlessEqual(nodes[0].children.name, "abc")

    def check_presence_empty(self, p):
        self.failUnlessEqual(p.get_from(), None)
        self.failUnlessEqual(p.get_to(), None)
        self.failUnlessEqual(p.get_type(), None)
        self.failUnlessEqual(p.get_id(), None)
        self.failUnlessEqual(p.get_show(), None)
        self.failUnlessEqual(p.get_status(), None)
        self.failUnlessEqual(p.get_priority(), 0)
        nodes = p.xpath_eval("t:payload",{"t":"http://pyxmpp.jajcus.net/xmlns/test"})
        self.failIf(nodes)

    def check_presence_subscribe(self, p):
        self.failUnlessEqual(p.get_from(), JID("source@example.com/res"))
        self.failUnlessEqual(p.get_to(), JID("dest@example.com"))
        self.failUnlessEqual(p.get_type(), "subscribe")
        self.failUnlessEqual(p.get_id(), None)
        self.failUnlessEqual(p.get_show(), None)
        self.failUnlessEqual(p.get_status(), None)

    def test_presence_full_from_xml(self):
        p = Presence(presence1_node)
        self.check_presence_full(p)

    def test_presence_empty_from_xml(self):
        p = Presence(presence2_node)
        self.check_presence_empty(p)

    def test_presence_subscribe_from_xml(self):
        p = Presence(presence3_node)
        self.check_presence_subscribe(p)

    def test_presence_empty(self):
        p = Presence()
        self.check_presence_empty(p)
        node, doc = self.stanza_to_xml(p)
        self.check_presence_empty( Presence(node) )
        node, doc = self.xml_to_xml(doc)
        self.check_presence_empty( Presence(node) )

    def test_presence_full(self):
        p = Presence(
                from_jid = JID("source@example.com/res"),
                to_jid = JID("dest@example.com"),
                stanza_type = None,
                stanza_id = u"1",
                show = u"away",
                status = u"The Status",
                priority = "10")
        n = p.xmlnode.newChild(None, "payload", None)
        ns = n.newNs("http://pyxmpp.jajcus.net/xmlns/test", "t")
        n.setNs(ns)
        n.newChild(ns, "abc", None)
        self.check_presence_full(p)
        node, doc = self.stanza_to_xml(p)
        self.check_presence_full( Presence(node) )
        xml = self.xml_to_xml(doc)
        self.check_presence_full( Presence(node) )

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
     suite.addTest(unittest.makeSuite(TestPresence))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
