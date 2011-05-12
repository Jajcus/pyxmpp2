#!/usr/bin/python -u
# -*- coding: UTF-8 -*-

import unittest
from xml.etree import ElementTree

from pyxmpp2.xmppserializer import XMPPSerializer, serialize
from pyxmpp2.jid import JID

def xml_elements_equal(a, b, ignore_level1_cdata = False):
    if a.tag != b.tag:
        return False
    a_attrs = a.items()
    a_attrs.sort()
    b_attrs = b.items()
    b_attrs.sort()

    if not ignore_level1_cdata:
        if a.text != b.text:
            return False

    if a_attrs != b_attrs:
        return False

    if len(a) != len(b):
        return False
    for ac, bc in zip(a, b):
        if ac.tag != bc.tag:
            return False
        if not ignore_level1_cdata:
            if a.text != b.text:
                return False
        if not xml_elements_equal(ac, bc):
            return False
    return True

class TestXMPPSerializer(unittest.TestCase):
    def test_emit_head(self):
        serializer = XMPPSerializer("jabber:client")
        output = serializer.emit_head("fromX", "toY")
        self.failUnless(output.startswith("<stream:stream "))
        self.failUnless("xmlns='jabber:client'" in output
                            or 'xmlns="jabber:client"' in output)
        xml = ElementTree.XML(output + "</stream:stream>")
        self.failUnlessEqual(xml.tag,
                                "{http://etherx.jabber.org/streams}stream")
        self.failUnlessEqual(xml.get('from'), 'fromX')
        self.failUnlessEqual(xml.get('to'), 'toY')
        self.failUnlessEqual(xml.get('version'), '1.0')
        self.failUnlessEqual(len(xml), 0)

    def test_emit_head_no_from_to(self):
        serializer = XMPPSerializer("jabber:client")
        output = serializer.emit_head(None, None)
        xml = ElementTree.XML(output + "</stream:stream>")
        self.failUnlessEqual(xml.get('from'), None)
        self.failUnlessEqual(xml.get('to'), None)

    def test_emit_tail(self):
        serializer = XMPPSerializer("jabber:client")
        output = serializer.emit_head("fromX", "toY")
        output += serializer.emit_tail()
        xml = ElementTree.XML(output)
        self.failUnlessEqual(len(xml), 0)

    def test_emit_stanza(self):
        serializer = XMPPSerializer("jabber:client")
        output = serializer.emit_head("from", "to")

        stanza = ElementTree.XML("<message xmlns='jabber:client'>"
                                    "<body>Body</body>"
                                    "<sub xmlns='http://example.org/ns'>"
                                        "<sub1 />"
                                    "<sub2 xmlns='http://example.org/ns2' />"
                                "</sub>"
                            "</message>")
        output += serializer.emit_stanza(stanza)
        output += serializer.emit_tail()
        print output
        xml = ElementTree.XML(output)
        self.failUnlessEqual(len(xml), 1)
        self.failUnlessEqual(len(xml[0]), 2)
        self.failUnless(xml_elements_equal(xml[0], stanza))

        # no prefix for stanza elements
        self.failUnless("<message><body>" in output)

        # no prefix for stanza child
        self.failUnless("<sub " in output)
        
        # ...and its same-namespace child
        self.failUnless("<sub1/" in output or "<sub1 " in output)

        # prefix for other namespace child
        self.failUnless("<ns1:sub2" in output)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestXMPPSerializer))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
