#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest

from xml.etree.ElementTree import Element, SubElement, XML

from pyxmpp2.iq import Iq
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence
from pyxmpp2.stanzaprocessor import stanza_factory, StanzaProcessor
from pyxmpp2.stanzapayload import XMLPayload
from pyxmpp2.jid import JID
from pyxmpp2.utils import xml_elements_equal


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

MESSAGE3 = """<message xmlns="jabber:client" type='chat'>
<body>Chat!</body>
</message>"""

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
PRESENCE4 = """<presence xmlns="jabber:client" to='source@example.com/res'
                                from='dest@example.com' type="subscribed" />"""

ALL_STANZAS = (IQ1, IQ2, IQ3, IQ4, MESSAGE1, MESSAGE2, MESSAGE3,
            PRESENCE1, PRESENCE2, PRESENCE3, PRESENCE4)
NON_IQ_STANZAS = (MESSAGE1, MESSAGE2, MESSAGE3, 
                    PRESENCE1, PRESENCE2, PRESENCE3, PRESENCE4)

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
        self.p.initiator = True

    def send(self, stanza):
        self.stanzas_sent.append(stanza)

    def process_stanzas(self, xml_elements):
        for xml in xml_elements:
            stanza = stanza_factory(XML(xml))
            self.p.process_stanza(stanza)

    def ignore_iq_get(self, stanza):
        self.handlers_called.append("ignore_iq_get")
        self.assertIsInstance(stanza, Iq)
        self.assertEqual(stanza.stanza_type, "get")
        return True

    def ignore_iq_set(self, stanza):
        self.handlers_called.append("ignore_iq_set")
        self.assertIsInstance(stanza, Iq)
        self.assertEqual(stanza.stanza_type, "set")
        return True

    def reply_iq_get(self, stanza):
        self.handlers_called.append("reply_iq_get")
        self.assertIsInstance(stanza, Iq)
        self.assertEqual(stanza.stanza_type, "get")
        reply = stanza.make_result_response()
        element = Element("{http://pyxmpp.jajcus.net/xmlns/test}payload")
        SubElement(element, "{http://pyxmpp.jajcus.net/xmlns/test}abc")
        reply.set_payload(element)
        return reply

    def reply_iq_set(self, stanza):
        self.handlers_called.append("reply_iq_set")
        self.assertIsInstance(stanza, Iq)
        self.assertEqual(stanza.stanza_type, "set")
        reply = stanza.make_result_response()
        return reply

    def echo_message(self, stanza):
        self.handlers_called.append("echo_message")
        self.assertIsInstance(stanza, Message)
        self.assertNotEqual(stanza.stanza_type, "error")
        message = Message(to_jid = stanza.from_jid,
                    from_jid = stanza.to_jid,
                    stanza_type = stanza.stanza_type,
                    thread = stanza.thread,
                    subject = stanza.subject,
                    body = stanza.body)
        return message
    
    def eat1(self, stanza):
        self.handlers_called.append("eat1")
        return True
    def eat2(self, stanza):
        self.handlers_called.append("eat2")
        return True
    def pass1(self, stanza):
        self.handlers_called.append("pass1")
    def pass2(self, stanza):
        self.handlers_called.append("pass2")

    def test_iq_ignore_handlers(self):
        self.p.set_iq_get_handler(XMLPayload, self.ignore_iq_get,
                    "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.p.set_iq_set_handler(XMLPayload, self.ignore_iq_set,
                    "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.process_stanzas(ALL_STANZAS)
        self.assertEqual(self.handlers_called, ["ignore_iq_get",
                                                    "ignore_iq_set"])
        self.assertFalse(self.stanzas_sent)

    def test_iq_reply_handlers(self):
        self.p.set_iq_get_handler(XMLPayload, self.reply_iq_get,
                    "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.p.set_iq_set_handler(XMLPayload, self.reply_iq_set,
                    "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        self.process_stanzas(ALL_STANZAS)
        self.assertEqual(self.handlers_called, ["reply_iq_get",
                                                    "reply_iq_set"])
        self.assertEqual(len(self.stanzas_sent), 2)
        stanza1 = self.stanzas_sent[0]
        self.assertTrue(xml_elements_equal(stanza1.as_xml(), XML(IQ2), True))
        stanza2 = self.stanzas_sent[1]
        self.assertTrue(xml_elements_equal(stanza2.as_xml(), XML(IQ4), True))

    def test_no_handlers(self):
        self.process_stanzas(ALL_STANZAS)
        self.assertEqual(self.handlers_called, [])
        self.assertFalse(self.handlers_called)
        self.assertEqual(len(self.stanzas_sent), 2)
        stanza1 = self.stanzas_sent[0]
        self.assertIsInstance(stanza1, Iq)
        self.assertEqual(stanza1.stanza_type, u"error")
        self.assertEqual(stanza1.error.condition_name,
                                        u"feature-not-implemented")
        self.assertEqual(stanza1.stanza_id, u"1")
        self.assertEqual(stanza1.to_jid, JID(u"source@example.com/res"))
        stanza2 = self.stanzas_sent[1]
        self.assertIsInstance(stanza2, Iq)
        self.assertEqual(stanza2.stanza_type, u"error")
        self.assertEqual(stanza2.error.condition_name,
                                        u"feature-not-implemented")
        self.assertEqual(stanza2.stanza_id, u"2")
        self.assertEqual(stanza2.to_jid, JID(u"source@example.com/res"))

    def test_message_handler(self):
        self.p.set_message_handler(None, self.echo_message)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["echo_message", "echo_message",
                                                        "echo_message"])
        self.assertEqual(len(self.stanzas_sent), 3)
        stanza1 = self.stanzas_sent[0]
        self.assertIsInstance(stanza1, Message)
        self.assertEqual(stanza1.stanza_type, u"normal")
        stanza2 = self.stanzas_sent[1]
        self.assertIsInstance(stanza2, Message)
        self.assertEqual(stanza2.stanza_type, None)
        stanza2 = self.stanzas_sent[2]
        self.assertIsInstance(stanza2, Message)
        self.assertEqual(stanza2.stanza_type, u"chat")

    def test_message_pass1_pass2(self):
        self.p.set_message_handler(None, self.pass1, priority = 10)
        self.p.set_message_handler(None, self.pass2, priority = 20)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1", "pass2",
                                        "pass1", "pass2", "pass1", "pass2"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_message_pass2_pass1(self):
        self.p.set_message_handler(None, self.pass1, priority = 20)
        self.p.set_message_handler(None, self.pass2, priority = 10)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass2", "pass1",
                                        "pass2", "pass1", "pass2", "pass1"])
        self.assertEqual(len(self.stanzas_sent), 0)


    def test_message_eat1_eat2(self):
        self.p.set_message_handler(None, self.eat1, priority = 10)
        self.p.set_message_handler(None, self.eat1, priority = 20)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["eat1", "eat1", "eat1"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_message_pass1_eat2(self):
        self.p.set_message_handler(None, self.pass1, priority = 10)
        self.p.set_message_handler(None, self.eat2, priority = 20)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1", "eat2", 
                                        "pass1", "eat2", "pass1", "eat2"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_message_chat_handler(self):
        self.p.set_message_handler("chat", self.pass1, priority = 10)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_presence_pass1_pass2(self):
        self.p.set_presence_handler(None, self.pass1, priority = 10)
        self.p.set_presence_handler(None, self.pass2, priority = 20)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1", "pass2",
                                                        "pass1", "pass2"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_presence_pass2_pass1(self):
        self.p.set_presence_handler(None, self.pass1, priority = 20)
        self.p.set_presence_handler(None, self.pass2, priority = 10)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass2", "pass1",
                                                        "pass2", "pass1"])
        self.assertEqual(len(self.stanzas_sent), 0)


    def test_presence_eat1_eat2(self):
        self.p.set_presence_handler(None, self.eat1, priority = 10)
        self.p.set_presence_handler(None, self.eat1, priority = 20)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["eat1", "eat1"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_presence_pass1_eat2(self):
        self.p.set_presence_handler(None, self.pass1, priority = 10)
        self.p.set_presence_handler(None, self.eat2, priority = 20)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1", "eat2", 
                                                    "pass1", "eat2"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_presence_subscribe_handler(self):
        self.p.set_presence_handler("subscribe", self.pass1, priority = 10)
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1"])
        self.assertEqual(len(self.stanzas_sent), 0)



def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestStanzaFactory))
     suite.addTest(unittest.makeSuite(TestStanzaProcessor))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
