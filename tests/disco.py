#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import libxml2
from pyxmpp.jabber import disco
from pyxmpp.jid import JID

class TestDiscoInfo(unittest.TestCase):
    def test_xml_input(self):
        xmldata=libxml2.parseFile("data/disco_info_in.xml")
        di=disco.DiscoInfo(xmldata.getRootElement())
        txt=`[(i.name(),i.category(),i.type()) for i in di.identities()]`
        txt+="\n"+`di.features()`+"\n"
        should_be=file("data/disco_info_in.txt").read()
        self.failUnlessEqual(txt,should_be)
#    def test_xml_output(self):
# def test_building(self):


test_items=[
    (JID("a@b.c"),None,None),
    (JID("a@b.c"),"d",None),
    (JID("f@b.c"),None,"e"),
    (JID("f@b.c"),"d","e"),
    ];
test_items.sort()

notest_items=[
    (JID("test@example.com"),None),
    (JID("test@example.com"),"d"),
    (JID("test@example.com"),"test"),
    (JID("a@b.c"),"test"),
    ];


class TestDiscoItems(unittest.TestCase):
    def test_xml_input(self):
        xmldata=libxml2.parseFile("data/disco_items_in.xml")
        di=disco.DiscoItems(xmldata.getRootElement())
        txt=`[(i.jid(),i.name(),i.node(),i.action()) for i in di.items()]`+"\n"
        should_be=file("data/disco_items_in.txt").read()
        self.failUnlessEqual(txt,should_be)

    def build_disco_items(self,node=None):
        di=disco.DiscoItems(node)
        for jid,node,name in test_items:
            di.add_item(jid,node,name)
        return di

    def test_xml_output(self):
        di=self.build_disco_items()
        txt=di.xmlnode.serialize()
        should_be=file("data/disco_items_out.xml").read()
        self.failUnlessEqual(txt,should_be)

    def test_building(self):
        self.build_disco_items()
    
    def test_building_with_node(self):
        di=self.build_disco_items("test")
        self.failUnlessEqual(di.node(),"test")

    def test_items(self):
        di=self.build_disco_items()
        actual_items=[(i.jid(),i.node(),i.name()) for i in di.items()]
        actual_items.sort()
        self.failUnlessEqual(actual_items,test_items)

    def test_has_item(self):
        di=self.build_disco_items()
        for jid,node,name in test_items:
            self.failUnless(di.has_item(jid,node))
        for jid,node in notest_items:
            self.failIf(di.has_item(jid,node))
        
        
def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestDiscoInfo))
     suite.addTest(unittest.makeSuite(TestDiscoItems))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4 encoding=utf-8
