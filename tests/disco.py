#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import libxml2
from pyxmpp.jabber import disco

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

class TestDiscoItems(unittest.TestCase):
    def test_xml_input(self):
        xmldata=libxml2.parseFile("data/disco_items_in.xml")
        di=disco.DiscoItems(xmldata.getRootElement())
        txt=`[(i.jid(),i.name(),i.node(),i.action()) for i in di.items()]`+"\n"
        should_be=file("data/disco_items_in.txt").read()
        self.failUnlessEqual(txt,should_be)

#    def test_xml_input(self):
#    def test_xml_output(self):
#    def test_building(self):
    
def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestDiscoInfo))
     suite.addTest(unittest.makeSuite(TestDiscoItems))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4 encoding=utf-8
