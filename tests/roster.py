#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import os
from Queue import Queue

from pyxmpp2.etree import ElementTree

import pyxmpp2.version
from pyxmpp2.iq import Iq
from pyxmpp2.jid import JID
from pyxmpp2.stanzaprocessor import StanzaProcessor
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.stanzapayload import XMLPayload
from pyxmpp2.exceptions import BadRequestProtocolError
from pyxmpp2.exceptions import NotAcceptableProtocolError
from pyxmpp2.mainloop.events import EventDispatcher
from pyxmpp2.streamevents import AuthorizedEvent

from pyxmpp2.roster import RosterItem, RosterPayload, Roster
from pyxmpp2.roster import RosterClient
from pyxmpp2.roster import RosterReceivedEvent, RosterNotReceivedEvent
from pyxmpp2.roster import RosterUpdatedEvent


IQ1 = '''<iq type="get" id="1" xmlns="jabber:client">
<query xmlns="jabber:iq:version"/>
</iq>'''

IQ2 = '''<iq type="response" id="1" xmlns="jabber:client">
<query xmlns="jabber:iq:version">
  <name>NAME</name>
  <version>VERSION</version>
  <os>OS</os>
</query>
</iq>'''

class TestRosterItem(unittest.TestCase):
    def test_parse_empty(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"/>')
        with self.assertRaises(BadRequestProtocolError):
            item = RosterItem.from_xml(element)

    def test_parse_only_jid(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                                                            ' jid="a@b.c"/>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertIsNone(item.name)
        self.assertEqual(item.groups, set())
        self.assertIsNone(item.subscription)
        self.assertIsNone(item.ask)
        self.assertFalse(item.approved)
        item.verify_roster_result()
        item.verify_roster_result(True)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertIsNone(item.name)
        self.assertEqual(item.groups, set())
        self.assertIsNone(item.subscription)
        self.assertIsNone(item.ask)
        self.assertFalse(item.approved)

    def test_parse_full(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                        ' jid="a@b.c" name="NAME" subscription="to"'
                        ' ask="subscribe" approved="true">'
                        '<group>GROUP1</group><group>GROUP2</group>'
                        '</item>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.name, u"NAME")
        self.assertEqual(item.groups, set(["GROUP1", "GROUP2"]))
        self.assertEqual(item.subscription, "to")
        self.assertEqual(item.ask, "subscribe")
        self.assertTrue(item.approved)
        item.verify_roster_result()
        item.verify_roster_result(True)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.name, u"NAME")
        self.assertEqual(item.groups, set(["GROUP1", "GROUP2"]))
        self.assertEqual(item.subscription, "to")
        self.assertEqual(item.ask, "subscribe")
        self.assertTrue(item.approved)

    def test_bad_subscription(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                        ' jid="a@b.c" name="NAME" subscription="bad"'
                        ' ask="subscribe" approved="true">'
                        '<group>GROUP1</group><group>GROUP2</group>'
                        '</item>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.name, u"NAME")
        self.assertEqual(item.groups, set(["GROUP1", "GROUP2"]))
        self.assertEqual(item.subscription, "bad")
        self.assertEqual(item.ask, "subscribe")
        self.assertTrue(item.approved)
        with self.assertRaises(ValueError):
            item.verify_roster_result()
        item.verify_roster_result(True)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.name, u"NAME")
        self.assertEqual(item.groups, set(["GROUP1", "GROUP2"]))
        self.assertIsNone(item.subscription)
        self.assertEqual(item.ask, "subscribe")
        self.assertTrue(item.approved)

    def test_result_with_remove(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                        ' jid="a@b.c" subscription="remove"/>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.subscription, "remove")
        with self.assertRaises(ValueError):
            item.verify_roster_result()
        item.verify_roster_result(True)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertIsNone(item.subscription)

    def test_push_with_remove(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                        ' jid="a@b.c" subscription="remove"/>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.subscription, "remove")
        item.verify_roster_push()
        item.verify_roster_push(True)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.subscription, "remove")

    def test_set_with_remove(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                        ' jid="a@b.c" subscription="remove"/>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.subscription, "remove")
        item.verify_roster_set()
        item.verify_roster_set(True)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.subscription, "remove")

    def test_set_with_subscription(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                        ' jid="a@b.c" subscription="both"/>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.subscription, "both")
        with self.assertRaises(BadRequestProtocolError):
            item.verify_roster_set()
        item.verify_roster_set(True)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertIsNone(item.subscription)

    def test_set_empty_group(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                        ' jid="a@b.c"><group/></item>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.groups, set([u""]))
        with self.assertRaises(NotAcceptableProtocolError):
            item.verify_roster_set()
        with self.assertRaises(NotAcceptableProtocolError):
            item.verify_roster_set(True)

    def test_set_duplicate_group(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                        ' jid="a@b.c"><group>GROUP1</group>'
                                    '<group>GROUP1</group></item>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.groups, set([u"GROUP1"]))
        with self.assertRaises(BadRequestProtocolError):
            item.verify_roster_set()
        with self.assertRaises(BadRequestProtocolError):
            item.verify_roster_set(True)

    def test_set_full(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"'
                        ' jid="a@b.c" name="NAME" subscription="to"'
                        ' ask="subscribe" approved="true">'
                        '<group>GROUP1</group><group>GROUP2</group>'
                        '</item>')
        item = RosterItem.from_xml(element)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.name, u"NAME")
        self.assertEqual(item.groups, set(["GROUP1", "GROUP2"]))
        self.assertEqual(item.subscription, "to")
        self.assertEqual(item.ask, "subscribe")
        self.assertTrue(item.approved)
        with self.assertRaises(BadRequestProtocolError):
            item.verify_roster_set()
        item.verify_roster_set(True)
        self.assertEqual(item.jid, JID("a@b.c"))
        self.assertEqual(item.name, u"NAME")
        self.assertEqual(item.groups, set(["GROUP1", "GROUP2"]))
        self.assertIsNone(item.subscription)
        self.assertIsNone(item.ask, None)
        self.assertFalse(item.approved)

class Processor(StanzaProcessor):
    def __init__(self, handlers):
        StanzaProcessor.__init__(self)
        self.setup_stanza_handlers(handlers, "post-auth")
        self.stanzas_sent = []
    def send(self, stanza):
        self.stanzas_sent.append(stanza)

class DummyStream(object):
    def __init__(self, features, me):
        self.features = features
        self.me = me

EMPTY_FEATURES = "<features xmlns:stream='http://etherx.jabber.org/streams'/>"
VERSION_FEATURES = (
    "<features xmlns:stream='http://etherx.jabber.org/streams'>"
        "<ver xmlns='urn:xmpp:features:rosterver'/>"
    "</features>")

class TestRosterClient(unittest.TestCase):
    def test_request_no_version(self):
        event_queue = Queue()
        settings = XMPPSettings()
        settings["event_queue"] = event_queue
        client = RosterClient(settings)
        dispatcher = EventDispatcher(settings, [client])
        self.assertIsNone(client.roster)
        self.assertTrue(event_queue.empty())
        processor = Processor([client])
        stream = DummyStream(ElementTree.XML(EMPTY_FEATURES),
                                                JID("test@example.org/Test"))
        event = AuthorizedEvent(JID("test@example.org/Test"))
        event.stream = stream
        event_queue.put(event)
        dispatcher.dispatch()
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        self.assertEqual(stanza.stanza_type, "get")
        self.assertIsNone(stanza.to_jid, None)
        xml = stanza.as_xml()
        self.assertEqual(xml[0].tag, "{jabber:iq:roster}query")
        self.assertEqual(len(xml[0]), 0)
        payload = stanza.get_payload(RosterPayload)
        self.assertEqual(len(payload), 0)
        self.assertIsNone(payload.version, None)
        response = stanza.make_result_response()
        item1 = RosterItem(JID("item1@example.org"))
        item2 = RosterItem(JID("item2@example.org"))
        payload = RosterPayload([item1, item2], None)
        response.set_payload(payload)
        processor.uplink_receive(response)
        self.assertIsNotNone(client.roster)
        self.assertEqual(len(client.roster), 2)
        self.assertTrue(JID("item1@example.org") in client.roster)
        self.assertTrue(JID("item2@example.org") in client.roster)
        self.assertIsNone(client.roster.version)
        event = event_queue.get_nowait()
        self.assertIsInstance(event, RosterReceivedEvent)
        self.assertEqual(event.roster_client, client)
        self.assertEqual(event.roster, client.roster)

    def test_request_version(self):
        event_queue = Queue()
        settings = XMPPSettings()
        settings["event_queue"] = event_queue
        client = RosterClient(settings)
        dispatcher = EventDispatcher(settings, [client])
        self.assertIsNone(client.roster)
        self.assertTrue(event_queue.empty())
        processor = Processor([client])
        stream = DummyStream(ElementTree.XML(VERSION_FEATURES),
                                                JID("test@example.org/Test"))
        event = AuthorizedEvent(JID("test@example.org/Test"))
        event.stream = stream
        event_queue.put(event)
        dispatcher.dispatch()
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        self.assertEqual(stanza.stanza_type, "get")
        self.assertIsNone(stanza.to_jid, None)
        payload = stanza.get_payload(RosterPayload)
        self.assertEqual(len(payload), 0)
        self.assertEqual(payload.version, u"")
        response = stanza.make_result_response()
        item1 = RosterItem(JID("item1@example.org"))
        item2 = RosterItem(JID("item2@example.org"))
        payload = RosterPayload([item1, item2], u"VERSION")
        response.set_payload(payload)
        processor.uplink_receive(response)
        self.assertIsNotNone(client.roster)
        self.assertEqual(len(client.roster), 2)
        self.assertTrue(JID("item1@example.org") in client.roster)
        self.assertTrue(JID("item2@example.org") in client.roster)
        self.assertEqual(client.roster.version, u"VERSION")
        event = event_queue.get_nowait()
        self.assertIsInstance(event, RosterReceivedEvent)
        self.assertEqual(event.roster_client, client)
        self.assertEqual(event.roster, client.roster)


def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestRosterItem))
     suite.addTest(unittest.makeSuite(TestRosterClient))
     return suite

if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.WARNING)
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
