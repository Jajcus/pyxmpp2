#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import libxml2
from pyxmpp import xmlextra
from stream_reader import xml_elements_equal

input_xml = """<?xml version="1.0" ?>
<root xmlns="http://pyxmpp.jabberstudio.org/xmlns/test" xmlns:prefix="http://pyxmpp.jabberstudio.org/xmlns/test1">
   <a> <a1/> <a2/> </a>
   <b xmlns="http://pyxmpp.jabberstudio.org/xmlns/test2">
     <c/>
     <prefix:d/>
   </b>
   <prefix:e/>
   <f/>
</root>
"""

output_xml = """<?xml version="1.0" ?>
<root xmlns="http://pyxmpp.jabberstudio.org/xmlns/common" xmlns:prefix="http://pyxmpp.jabberstudio.org/xmlns/test1">
   <a> <a1/> <a2/> </a>
   <b xmlns="http://pyxmpp.jabberstudio.org/xmlns/test2">
     <c/>
     <prefix:d/>
   </b>
   <prefix:e/>
   <f/>
</root>
"""

input_doc = libxml2.parseDoc(input_xml)
input_root = input_doc.getRootElement()
output_doc = libxml2.parseDoc(output_xml)
output_root = output_doc.getRootElement()

class TestReplaceNs(unittest.TestCase):
    def test_replace_ns(self):
        doc = libxml2.newDoc("1.0")
        
        root = doc.newChild(None, "root", None)
        common_ns = root.newNs(xmlextra.COMMON_NS, None)
        root.setNs(common_ns)
        doc.setRootElement(root)
        
        n = input_doc.getRootElement()
        input_ns = n.ns()
        n = n.children
        while n:
            n1 = n.docCopyNode(doc, 1)
            root.addChild(n1)
            if n1.type == 'element':
                n1_ns = n1.ns()
                if n1_ns.content == input_ns.content:
                    xmlextra.replace_ns(n1, n1_ns, common_ns)
            n = n.next
        #print doc.serialize()
        self.failUnless(xml_elements_equal(root, output_root))

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestReplaceNs))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4 encoding=utf-8
