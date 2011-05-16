#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.iq import Iq
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence
from pyxmpp2.stanzaprocessor import stanza_factory, StanzaProcessor
from pyxmpp2.jid import JID

IQ1 = """
<iq xmlns="jabber:client" from='source@example.com/res' 
                                to='dest@example.com' type='get' id='1'>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</iq>"""

IQ2 = """
<iq xmlns="jabber:client" to='source@example.com/res' 
                                from='dest@example.com' type='result' id='1'>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</iq>"""

IQ3 = """
<iq xmlns="jabber:client" from='source@example.com/res' 
                                to='dest@example.com' type='set' id='2'>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</iq>"""

IQ4 = """
<iq xmlns="jabber:client" to='source@example.com/res' 
                                from='dest@example.com' type='result' id='2'>
</iq>"""

MESSAGE1 = """
<message xmlns="jabber:client" from='source@example.com/res' 
                                to='dest@example.com' type='normal' id='1'>
<subject>Subject</subject>
<body>The body</body>
<thread>thread-id</thread>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</message>"""

MESSAGE2 = """<message xmlns="jabber:client"/>"""

PRESENCE1 = """
<presence xmlns="jabber:client" from='source@example.com/res'
                                            to='dest@example.com' id='1'>
<show>away</show>
<status>The Status</status>
<priority>10</priority>
<payload xmlns="http://pyxmpp.jajcus.net/xmlns/test"><abc/></payload>
</presence>"""

PRESENCE2 = """<presence xmlns="jabber:client"/>"""

PRESENCE3 = """<presence xmlns="jabber:client" from='source@example.com/res'
                                to='dest@example.com' type="subscribe" />"""

ALL_STANZAS = (IQ1, IQ2, IQ3, IQ4, MESSAGE1, MESSAGE2, PRESENCE1, PRESENCE2,
                PRESENCE3)

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

class TestStanzaProcessor(unittest.TestCase):
    def setUp(self):
        self.handlers_called = []
        self.stanzas_sent = []
        self.p = StanzaProcessor()
        self.p.me = JID("dest@example.com/xx")
        self.p.peer = JID("source@example.com/yy")
        self.p.send = self.send

    def send(self, stanza):
        self.stanzas_sent.append(stanza)

    def process_stanzas(self, xml_elements):
        for xml in xml_elements:
            stanza = stanza_factory(XML(xml))
            self.p.process_stanza(stanza)

    def test_no_handlers(self):
        self.process_stanzas(ALL_STANZAS)
        self.assertEqual(self.handlers_called, [])

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestStanzaFactory))
     suite.addTest(unittest.makeSuite(TestStanzaProcessor))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
