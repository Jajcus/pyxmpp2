#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest

from pyxmpp2.etree import ElementTree

from pyxmpp2.iq import Iq
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence
from pyxmpp2.stanzaprocessor import stanza_factory, StanzaProcessor
from pyxmpp2.interfaces import XMPPFeatureHandler
from pyxmpp2.interfaces import iq_get_stanza_handler
from pyxmpp2.interfaces import iq_set_stanza_handler
from pyxmpp2.interfaces import message_stanza_handler
from pyxmpp2.interfaces import presence_stanza_handler
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
        element = ElementTree.XML(IQ1)
        stanza = stanza_factory(element)
        self.assertTrue( isinstance(stanza, Iq) )
    def test_message(self):
        element = ElementTree.XML(MESSAGE1)
        stanza = stanza_factory(element)
        self.assertTrue( isinstance(stanza, Message) )
    def test_presence(self):
        element = ElementTree.XML(PRESENCE1)
        stanza = stanza_factory(element)
        self.assertTrue( isinstance(stanza, Presence) )

class TestStanzaProcessor(unittest.TestCase):
    # pylint: disable=R0904
    def setUp(self):
        self.handlers_called = []
        self.stanzas_sent = []
        self.proc = StanzaProcessor()
        self.proc.me = JID("dest@example.com/xx")
        self.proc.peer = JID("source@example.com/yy")
        self.proc.send = self.send
        self.proc.initiator = True

    def send(self, stanza):
        self.stanzas_sent.append(stanza)

    def process_stanzas(self, xml_elements):
        for xml in xml_elements:
            stanza = stanza_factory(ElementTree.XML(xml))
            self.proc.process_stanza(stanza)

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
        element = ElementTree.Element(
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
        ElementTree.SubElement(element,
                                    "{http://pyxmpp.jajcus.net/xmlns/test}abc")
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
        # pylint: disable=W0613
        self.handlers_called.append("eat1")
        return True
    def eat2(self, stanza):
        # pylint: disable=W0613
        self.handlers_called.append("eat2")
        return True
    def pass1(self, stanza):
        # pylint: disable=W0613
        self.handlers_called.append("pass1")
    def pass2(self, stanza):
        # pylint: disable=W0613
        self.handlers_called.append("pass2")

    def test_iq_ignore_handlers(self):
        parent = self
        class Handlers(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @iq_get_stanza_handler(XMLPayload,
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
            def handler1(self, stanza):
                return parent.ignore_iq_get(stanza)
            @iq_set_stanza_handler(XMLPayload,
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
            def handler2(self, stanza):
                return parent.ignore_iq_set(stanza)
        self.proc.setup_stanza_handlers([Handlers()], "post-auth")
        self.process_stanzas(ALL_STANZAS)
        self.assertEqual(self.handlers_called, ["ignore_iq_get",
                                                    "ignore_iq_set"])
        self.assertFalse(self.stanzas_sent)

    def test_iq_reply_handlers(self):
        parent = self
        class Handlers(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @iq_get_stanza_handler(XMLPayload,
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
            def handler1(self, stanza):
                return parent.reply_iq_get(stanza)
            @iq_set_stanza_handler(XMLPayload,
                                "{http://pyxmpp.jajcus.net/xmlns/test}payload")
            def handler2(self, stanza):
                return parent.reply_iq_set(stanza)
        self.proc.setup_stanza_handlers([Handlers()], "post-auth")
        self.process_stanzas(ALL_STANZAS)
        self.assertEqual(self.handlers_called, ["reply_iq_get",
                                                    "reply_iq_set"])
        self.assertEqual(len(self.stanzas_sent), 2)
        stanza1 = self.stanzas_sent[0]
        self.assertTrue(xml_elements_equal(stanza1.as_xml(),
                                                    ElementTree.XML(IQ2), True))
        stanza2 = self.stanzas_sent[1]
        self.assertTrue(xml_elements_equal(stanza2.as_xml(),
                                                    ElementTree.XML(IQ4), True))

    def test_no_handlers(self):
        self.process_stanzas(ALL_STANZAS)
        self.assertEqual(self.handlers_called, [])
        self.assertFalse(self.handlers_called)
        self.assertEqual(len(self.stanzas_sent), 2)
        stanza1 = self.stanzas_sent[0]
        self.assertIsInstance(stanza1, Iq)
        self.assertEqual(stanza1.stanza_type, u"error")
        self.assertEqual(stanza1.error.condition_name, u"service-unavailable")
        self.assertEqual(stanza1.stanza_id, u"1")
        self.assertEqual(stanza1.to_jid, JID(u"source@example.com/res"))
        stanza2 = self.stanzas_sent[1]
        self.assertIsInstance(stanza2, Iq)
        self.assertEqual(stanza2.stanza_type, u"error")
        self.assertEqual(stanza2.error.condition_name, u"service-unavailable")
        self.assertEqual(stanza2.stanza_id, u"2")
        self.assertEqual(stanza2.to_jid, JID(u"source@example.com/res"))

    def test_message_handler(self):
        parent = self
        class Handlers(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler()
            def handler1(self, stanza):
                return parent.echo_message(stanza)
        self.proc.setup_stanza_handlers([Handlers()], "post-auth")
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
        parent = self
        class Handlers1(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler()
            def handler1(self, stanza):
                return parent.pass1(stanza)
        class Handlers2(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler()
            def handler1(self, stanza):
                return parent.pass2(stanza)
        self.proc.setup_stanza_handlers([Handlers1(), Handlers2()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1", "pass2",
                                        "pass1", "pass2", "pass1", "pass2"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_message_pass2_pass1(self):
        parent = self
        class Handlers1(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler()
            def handler1(self, stanza):
                return parent.pass1(stanza)
        class Handlers2(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler()
            def handler1(self, stanza):
                return parent.pass2(stanza)
        self.proc.setup_stanza_handlers([Handlers2(), Handlers1()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass2", "pass1",
                                        "pass2", "pass1", "pass2", "pass1"])
        self.assertEqual(len(self.stanzas_sent), 0)


    def test_message_eat1_eat2(self):
        parent = self
        class Handlers1(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler()
            def handler1(self, stanza):
                return parent.eat1(stanza)
        class Handlers2(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler()
            def handler1(self, stanza):
                return parent.eat2(stanza)
        self.proc.setup_stanza_handlers([Handlers1(), Handlers2()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["eat1", "eat1", "eat1"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_message_pass1_eat2(self):
        parent = self
        class Handlers1(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler()
            def handler1(self, stanza):
                return parent.pass1(stanza)
        class Handlers2(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler()
            def handler1(self, stanza):
                return parent.eat2(stanza)
        self.proc.setup_stanza_handlers([Handlers1(), Handlers2()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1", "eat2",
                                        "pass1", "eat2", "pass1", "eat2"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_message_chat_handler(self):
        parent = self
        class Handlers(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @message_stanza_handler("chat")
            def handler1(self, stanza):
                return parent.pass1(stanza)
        self.proc.setup_stanza_handlers([Handlers()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_presence_pass1_pass2(self):
        parent = self
        class Handlers1(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @presence_stanza_handler()
            def handler1(self, stanza):
                return parent.pass1(stanza)
        class Handlers2(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @presence_stanza_handler()
            def handler1(self, stanza):
                return parent.pass2(stanza)
        self.proc.setup_stanza_handlers([Handlers1(), Handlers2()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1", "pass2",
                                                        "pass1", "pass2"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_presence_pass2_pass1(self):
        parent = self
        class Handlers1(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @presence_stanza_handler()
            def handler1(self, stanza):
                return parent.pass1(stanza)
        class Handlers2(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @presence_stanza_handler()
            def handler1(self, stanza):
                return parent.pass2(stanza)
        self.proc.setup_stanza_handlers([Handlers2(), Handlers1()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass2", "pass1",
                                                        "pass2", "pass1"])
        self.assertEqual(len(self.stanzas_sent), 0)


    def test_presence_eat1_eat2(self):
        parent = self
        class Handlers1(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @presence_stanza_handler()
            def handler1(self, stanza):
                return parent.eat1(stanza)
        class Handlers2(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @presence_stanza_handler()
            def handler1(self, stanza):
                return parent.eat2(stanza)
        self.proc.setup_stanza_handlers([Handlers1(), Handlers2()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["eat1", "eat1"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_presence_pass1_eat2(self):
        parent = self
        class Handlers1(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @presence_stanza_handler()
            def handler1(self, stanza):
                return parent.pass1(stanza)
        class Handlers2(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @presence_stanza_handler()
            def handler1(self, stanza):
                return parent.eat2(stanza)
        self.proc.setup_stanza_handlers([Handlers1(), Handlers2()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1", "eat2",
                                                    "pass1", "eat2"])
        self.assertEqual(len(self.stanzas_sent), 0)

    def test_presence_subscribe_handler(self):
        parent = self
        class Handlers(XMPPFeatureHandler):
            # pylint: disable=W0232,R0201,R0903
            @presence_stanza_handler("subscribe")
            def handler1(self, stanza):
                return parent.pass1(stanza)
        self.proc.setup_stanza_handlers([Handlers()], "post-auth")
        self.process_stanzas(NON_IQ_STANZAS)
        self.assertEqual(self.handlers_called, ["pass1"])
        self.assertEqual(len(self.stanzas_sent), 0)

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
