#!/usr/bin/python -u
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest
from xml.etree import ElementTree

from pyxmpp2.xmppserializer import XMPPSerializer

from pyxmpp2.utils import xml_elements_equal

class TestXMPPSerializer(unittest.TestCase):
    def test_emit_head(self):
        serializer = XMPPSerializer("jabber:client")
        output = serializer.emit_head("fromX", "toY")
        self.assertTrue(output.startswith("<stream:stream "))
        self.assertTrue("xmlns='jabber:client'" in output
                            or 'xmlns="jabber:client"' in output)
        self.assertFalse("xmlns:xml" in output)
        xml = ElementTree.XML(output + "</stream:stream>")
        self.assertEqual(xml.tag,
                                "{http://etherx.jabber.org/streams}stream")
        self.assertEqual(xml.get('from'), 'fromX')
        self.assertEqual(xml.get('to'), 'toY')
        self.assertEqual(xml.get('version'), '1.0')
        self.assertEqual(len(xml), 0)

    def test_emit_head_no_from_to(self):
        serializer = XMPPSerializer("jabber:client")
        output = serializer.emit_head(None, None)
        xml = ElementTree.XML(output + "</stream:stream>")
        self.assertEqual(xml.get('from'), None)
        self.assertEqual(xml.get('to'), None)

    def test_emit_tail(self):
        serializer = XMPPSerializer("jabber:client")
        output = serializer.emit_head("fromX", "toY")
        output += serializer.emit_tail()
        xml = ElementTree.XML(output)
        self.assertEqual(len(xml), 0)

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
        xml = ElementTree.XML(output)
        self.assertEqual(len(xml), 1)
        self.assertEqual(len(xml[0]), 2)
        self.assertTrue(xml_elements_equal(xml[0], stanza))

        # no prefix for stanza elements
        self.assertTrue("<message><body>" in output)

        # no prefix for stanza child
        self.assertTrue("<sub " in output)
        
        # ...and its same-namespace child
        self.assertTrue("<sub1/" in output or "<sub1 " in output)

        # prefix for other namespace child
        self.assertTrue("<sub2" in output)

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
