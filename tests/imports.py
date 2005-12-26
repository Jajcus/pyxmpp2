#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest

import pyxmpp.all as pyxmpp
import pyxmpp.jabber.all
import pyxmpp.jabberd.all

class TestImports(unittest.TestCase):
    def test_Stream(self):
        import pyxmpp.stream as m2
        self.failUnless(pyxmpp.Stream is m2.Stream,"Stream not imported correctly")
    def test_Stream_from(self):
        from pyxmpp import Stream as n1
        import pyxmpp.stream as m2
        self.failUnless(n1 is m2.Stream,"Stream not imported correctly")
    def test_JID(self):
        import pyxmpp.jid as m2
        self.failUnless(pyxmpp.JID is m2.JID,"JID not imported correctly")
    def test_JID_from(self):
        from pyxmpp import JID as n1
        import pyxmpp.jid as m2
        self.failUnless(n1 is m2.JID,"JID not imported correctly")
    def test_JabberClient(self):
        import pyxmpp.jabber.client as m2
        self.failUnless(pyxmpp.jabber.Client is m2.JabberClient,"JabberClient not imported correctly")
    def test_JabberClient_from(self):
        from pyxmpp.jabber import Client as n1
        import pyxmpp.jabber.client as m2
        self.failUnless(n1 is m2.JabberClient,"JabberClient not imported correctly")
    def test_Component(self):
        import pyxmpp.jabberd.component as m2
        self.failUnless(pyxmpp.jabberd.Component is m2.Component,"Component not imported correctly")
    def test_Component_from(self):
        from pyxmpp.jabberd import Component as n1
        import pyxmpp.jabberd.component as m2
        self.failUnless(n1 is m2.Component,"Component not imported correctly")

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestImports))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
