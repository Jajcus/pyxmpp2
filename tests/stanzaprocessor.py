#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.iq import Iq
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence
from pyxmpp2.stanzaprocessor import stanza_factory, StanzaProcessor

IQ1 = """
<iq xmlns="jabber:client" from='source@example.com/res' 
                                to='dest@example.com' type='get' id='1'>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</iq>"""

MESSAGE1 = """
<message xmlns="jabber:client" from='source@example.com/res' 
                                to='dest@example.com' type='normal' id='1'>
<subject>Subject</subject>
<body>The body</body>
<thread>thread-id</thread>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</message>"""

PRESENCE1 = """
<presence xmlns="jabber:client" from='source@example.com/res'
                                            to='dest@example.com' id='1'>
<show>away</show>
<status>The Status</status>
<priority>10</priority>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</presence>"""

class TestStanzaFactory(unittest.TestCase):
    def test_iq(self):
        element = XML(IQ1)
        stanza = stanza_factory(element)
        self.assertTrue( isinstance(stanza, Iq) )
    def test_message(self):
        element = XML(MESSAGE1)
        stanza = stanza_factory(element)
        self.assertTrue( isinstance(stanza, Message) )
    def test_presence(self):
        element = XML(PRESENCE1)
        stanza = stanza_factory(element)
        self.assertTrue( isinstance(stanza, Presence) )

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestStanzaFactory))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
