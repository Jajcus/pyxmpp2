#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import libxml2
from pyxmpp.jabber import disco
from pyxmpp.jid import JID

test_identities=[
        (u"Test",u"category",u"type"),
        (u"Test2",u"category2",u"type"),
        (u"Test3",u"category",u"type2"),
        (u"Teścik",u"ółńść",u"źółńś"),
        ];
test_identities.sort()

notest_identities=[
        (u"category",u"another-type"),
        (u"category3",u"type"),
        (u"category4",None),
        ];

test_features=[
    u"test-feature",
    u"http://jabber.org/protocol/disco#info",
#    u"http://dżabber.example.com/example-namespace",
    ];
test_features.sort()

notest_features=[
    u"another-test-feature",
    u"http://jabber.org/protocol/disco#items",
    u"http://dżabber.example.com/another-example-namespace",
    ];


class TestDiscoInfo(unittest.TestCase):
    def test_xml_input(self):
        xmldata=libxml2.parseFile("data/disco_info_in.xml")
        di=disco.DiscoInfo(xmldata.getRootElement())
        txt=`[(i.name,i.category,i.type) for i in di.identities]`
        txt+="\n"+`di.features`+"\n"
        should_be=file("data/disco_info_in.txt").read()
        self.failUnlessEqual(txt,should_be)

    def build_disco_info(self,node=None):
        di=disco.DiscoInfo(node)
        for name,category,type in test_identities:
            di.add_identity(name,category,type)
        for var in test_features:
            di.add_feature(var)
        return di

#    def test_xml_output(self):

    def test_building(self):
        self.build_disco_info()

    def test_building_with_node(self):
        di=self.build_disco_info("test")
        self.failUnlessEqual(di.node,"test")

    def test_identities(self):
        di=self.build_disco_info()
        actual_identities=[(i.name,i.category,i.type) for i in di.identities]
        actual_identities.sort()
        self.failUnlessEqual(actual_identities,test_identities)

    def test_features(self):
        di=self.build_disco_info()
        actual_features=di.get_features()
        actual_features.sort()
        self.failUnlessEqual(actual_features,test_features)

    def test_identity_is(self):
        di=self.build_disco_info()
        for name,category,type in test_identities:
            self.failUnless(di.identity_is(category,type),
                "Identity (%r,%r) not matched" % (category,type))
            self.failUnless(di.identity_is(category,None),
                "Identity (%r,%r) not matched" % (category,None))
        for category,type in notest_identities:
            self.failIf(di.identity_is(category,type),
                "Identity (%r,%r) matched" % (category,type))

    def test_has_feature(self):
        di=self.build_disco_info()
        for var in test_features:
            self.failUnless(di.has_feature(var),"Feature %r not found" % (var,))
        for var in notest_features:
            self.failIf(di.has_feature(var),"Feature %r found" % (var,))


# def test_building(self):


test_items=[
    (JID(u"a@b.c"),None,None),
    (JID(u"a@b.c"),u"d",None),
    (JID(u"f@b.c"),None,u"e"),
    (JID(u"f@b.c"),u"d",u"e"),
    (JID(u"użytkownik@dżabber"),u"węzeł",u"Teścik"),
    ];
test_items.sort()

notest_items=[
    (JID(u"test@example.com"),None),
    (JID(u"test@example.com"),u"d"),
    (JID(u"test@example.com"),u"test"),
    (JID(u"a@b.c"),u"test"),
    (JID(u"użytkownik2@dżabber"),u"węzeł"),
    ];

class TestDiscoItems(unittest.TestCase):
    def test_xml_input(self):
        xmldata=libxml2.parseFile("data/disco_items_in.xml")
        di=disco.DiscoItems(xmldata.getRootElement())
        txt=`[(i.jid,i.name,i.node,i.action) for i in di.items]`+"\n"
        should_be=file("data/disco_items_in.txt").read()
        self.failUnlessEqual(txt,should_be)

    def build_disco_items(self,node=None):
        di=disco.DiscoItems(node)
        for jid,node,name in test_items:
            di.add_item(jid,node,name)
        return di

    def test_xml_output(self):
        di=self.build_disco_items()
        txt=di.as_xml().serialize()
        should_be=file("data/disco_items_out.xml").read()
        self.failUnlessEqual(txt,should_be)

    def test_building(self):
        self.build_disco_items()

    def test_building_with_node(self):
        di=self.build_disco_items("test")
        self.failUnlessEqual(di.node,"test")

    def test_items(self):
        di=self.build_disco_items()
        actual_items=[(i.jid,i.node,i.name) for i in di.items]
        actual_items.sort()
        self.failUnlessEqual(actual_items,test_items)

    def test_has_item(self):
        di=self.build_disco_items()
        for jid,node,name in test_items:
            self.failUnless(di.has_item(jid,node),"Item (%r,%r) not found" % (jid,node))
        for jid,node in notest_items:
            self.failIf(di.has_item(jid,node),"Item (%r,%r) found" % (jid,node))

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestDiscoInfo))
     suite.addTest(unittest.makeSuite(TestDiscoItems))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
