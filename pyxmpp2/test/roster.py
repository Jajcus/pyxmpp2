#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest
from Queue import Queue

from pyxmpp2.etree import ElementTree

from pyxmpp2.iq import Iq
from pyxmpp2.jid import JID
from pyxmpp2.stanzaprocessor import StanzaProcessor
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.exceptions import BadRequestProtocolError
from pyxmpp2.exceptions import NotAcceptableProtocolError
from pyxmpp2.mainloop.events import EventDispatcher
from pyxmpp2.streamevents import AuthorizedEvent, GotFeaturesEvent

from pyxmpp2.roster import RosterItem, RosterPayload, Roster
from pyxmpp2.roster import RosterClient
from pyxmpp2.roster import RosterReceivedEvent, RosterNotReceivedEvent

class TestRosterItem(unittest.TestCase):
    def test_parse_empty(self):
        element = ElementTree.XML('<item xmlns="jabber:iq:roster"/>')
        with self.assertRaises(BadRequestProtocolError):
            RosterItem.from_xml(element)

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

    def test_build_empty(self):
        item = RosterItem(JID("test@example.org"))
        self.assertEqual(item.jid, JID("test@example.org"))
        self.assertIsNone(item.name)
        self.assertIsNone(item.subscription)
        self.assertIsNone(item.ask)
        self.assertFalse(item.approved)
        self.assertEqual(item.groups, set())
        xml = item.as_xml()
        self.assertEqual(xml.tag, "{jabber:iq:roster}item")
        self.assertEqual(len(xml), 0)
        self.assertEqual(xml.get("jid"), u"test@example.org")
        self.assertEqual(xml.get("name"), None)
        self.assertEqual(xml.get("subscription"), None)
        self.assertEqual(xml.get("ask"), None)
        self.assertEqual(xml.get("approved"), None)

        # check if serializable
        self.assertTrue(ElementTree.tostring(xml))

    def test_build_full(self):
        item = RosterItem(JID("test@example.org"), "NAME", ["G1", "G2"],
                                "from", "subscribe", "true")
        self.assertEqual(item.jid, JID("test@example.org"))
        self.assertEqual(item.name, "NAME")
        self.assertEqual(item.subscription, "from")
        self.assertEqual(item.ask, "subscribe")
        self.assertTrue(item.approved)
        self.assertEqual(item.groups, set(["G1", "G2"]))
        xml = item.as_xml()
        self.assertEqual(xml.tag, "{jabber:iq:roster}item")
        self.assertEqual(len(xml), 2)
        self.assertEqual(xml.get("jid"), u"test@example.org")
        self.assertEqual(xml.get("name"), "NAME")
        self.assertEqual(xml.get("subscription"), "from")
        self.assertEqual(xml.get("ask"), "subscribe")
        self.assertEqual(xml.get("approved"), "true")
        self.assertEqual(xml[0].tag, "{jabber:iq:roster}group")
        self.assertEqual(xml[1].tag, "{jabber:iq:roster}group")
        self.assertEqual(set([xml[0].text, xml[1].text]), set(["G1", "G2"]))

        # check if serializable
        self.assertTrue(ElementTree.tostring(xml))

class Processor(StanzaProcessor):
    def __init__(self, handlers):
        StanzaProcessor.__init__(self)
        self.setup_stanza_handlers(handlers, "post-auth")
        self.stanzas_sent = []
    def send(self, stanza):
        self.stanzas_sent.append(stanza)

class DummyStream(object):
    # pylint: disable=R0903
    def __init__(self, features, me):
        self.features = features
        self.me = me

EMPTY_FEATURES = "<features xmlns:stream='http://etherx.jabber.org/streams'/>"
VERSION_FEATURES = (
    "<features xmlns:stream='http://etherx.jabber.org/streams'>"
        "<ver xmlns='urn:xmpp:features:rosterver'/>"
    "</features>")

class TestRosterClient(unittest.TestCase):
    def test_get_no_version(self):
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

    def test_get_version(self):
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
        event = GotFeaturesEvent(stream.features)
        event.stream = stream
        event_queue.put(event)
        dispatcher.dispatch()
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

    def test_get_error(self):
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
        stanza = processor.stanzas_sent[0]
        response = stanza.make_error_response("item-not-found")
        processor.uplink_receive(response)
        self.assertIsNone(client.roster)
        event = event_queue.get_nowait()
        self.assertIsInstance(event, RosterNotReceivedEvent)
        self.assertEqual(event.roster_client, client)
        self.assertIsNotNone(event.stanza)
        self.assertEqual(event.stanza.stanza_id, response.stanza_id)

    def test_add_item(self):
        event_queue = Queue()
        settings = XMPPSettings()
        settings["event_queue"] = event_queue
        client = RosterClient(settings)
        processor = Processor([client])
        item1 = RosterItem(JID("item1@example.org"))
        item2 = RosterItem(JID("item2@example.org"))
        client.roster = Roster([item1, item2])

        # simple add
        client.add_item(JID("item3@example.org"))
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item3@example.org"))
        self.assertIsNone(item.name)
        self.assertIsNone(item.subscription)
        self.assertFalse(item.approved)
        self.assertFalse(item.groups)
        response = stanza.make_result_response()
        processor.uplink_receive(response)
        self.assertEqual(len(client.roster), 2) # not added yet, push needed

        # duplicate
        processor.stanzas_sent = []
        with self.assertRaises(ValueError):
            client.add_item(JID("item2@example.org"))
        self.assertEqual(len(processor.stanzas_sent), 0)

        # add with name and groups
        processor.stanzas_sent = []
        client.add_item(JID("item4@example.org"), "NAME", ["GROUP1", "GROUP2"])
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item4@example.org"))
        self.assertEqual(item.name, "NAME")
        self.assertEqual(item.groups, set(["GROUP1", "GROUP2"]))
        self.assertIsNone(item.subscription)
        self.assertFalse(item.approved)
        response = stanza.make_result_response()
        processor.uplink_receive(response)

        def callback(item):
            callback_calls.append(item)
        def error_callback(stanza):
            error_callback_calls.append(stanza)

        # callback
        processor.stanzas_sent = []
        callback_calls = []
        error_callback_calls = []
        client.add_item(JID("item5@example.org"),
                            callback = callback,
                            error_callback = error_callback)
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item5@example.org"))
        response = stanza.make_result_response()
        processor.uplink_receive(response)
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0].jid, JID("item5@example.org"))
        self.assertEqual(len(error_callback_calls), 0)

        # error callback
        processor.stanzas_sent = []
        callback_calls = []
        error_callback_calls = []
        client.add_item(JID("item5@example.org"),
                            callback = callback,
                            error_callback = error_callback)
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item5@example.org"))
        response = stanza.make_error_response("not-acceptable")
        processor.uplink_receive(response)
        self.assertEqual(len(callback_calls), 0)
        self.assertEqual(len(error_callback_calls), 1)
        stanza = error_callback_calls[0]
        self.assertIsInstance(stanza, Iq)
        self.assertEqual(stanza.stanza_id, response.stanza_id)

    def test_update_item(self):
        event_queue = Queue()
        settings = XMPPSettings()
        settings["event_queue"] = event_queue
        client = RosterClient(settings)
        processor = Processor([client])
        item1 = RosterItem(JID("item1@example.org"), "ITEM1")
        item2 = RosterItem(JID("item2@example.org"), groups = [
                                                        "GROUP1", "GROUP2"])
        client.roster = Roster([item1, item2])

        # update name
        client.update_item(JID("item2@example.org"), "NEW_NAME")
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item2@example.org"))
        self.assertEqual(item.name, "NEW_NAME")
        self.assertEqual(item.groups, set(["GROUP1", "GROUP2"]))
        self.assertIsNone(item.subscription)
        self.assertFalse(item.approved)
        response = stanza.make_result_response()
        processor.uplink_receive(response)

        # update groups
        processor.stanzas_sent = []
        client.update_item(JID("item2@example.org"), groups = ["GROUP3"])
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item2@example.org"))
        self.assertIsNone(item.name)
        self.assertEqual(item.groups, set(["GROUP3"]))
        self.assertIsNone(item.subscription)
        self.assertFalse(item.approved)
        response = stanza.make_result_response()
        processor.uplink_receive(response)

        # clear name
        processor.stanzas_sent = []
        client.update_item(JID("item1@example.org"), name = None)
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item1@example.org"))
        self.assertIsNone(item.name)
        self.assertEqual(item.groups, set([]))
        self.assertIsNone(item.subscription)
        self.assertFalse(item.approved)
        response = stanza.make_result_response()
        processor.uplink_receive(response)

        # clear groups
        processor.stanzas_sent = []
        client.update_item(JID("item2@example.org"), groups = None)
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item2@example.org"))
        self.assertIsNone(item.name)
        self.assertEqual(item.groups, set([]))
        self.assertIsNone(item.subscription)
        self.assertFalse(item.approved)
        response = stanza.make_result_response()
        processor.uplink_receive(response)

        # missing item
        processor.stanzas_sent = []
        with self.assertRaises(KeyError):
            client.update_item(JID("item3@example.org"), name = "NEW_NAME")
        self.assertEqual(len(processor.stanzas_sent), 0)

        def callback(item):
            callback_calls.append(item)
        def error_callback(stanza):
            error_callback_calls.append(stanza)

        # callback
        processor.stanzas_sent = []
        callback_calls = []
        error_callback_calls = []
        client.update_item(JID("item1@example.org"),
                            name = "NEW_NAME",
                            callback = callback,
                            error_callback = error_callback)
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item1@example.org"))
        self.assertEqual(item.name, "NEW_NAME")
        response = stanza.make_result_response()
        processor.uplink_receive(response)
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0].jid, JID("item1@example.org"))
        self.assertEqual(len(error_callback_calls), 0)

        # error callback
        processor.stanzas_sent = []
        callback_calls = []
        error_callback_calls = []
        client.update_item(JID("item1@example.org"),
                            name = "NEW_NAME",
                            callback = callback,
                            error_callback = error_callback)
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item1@example.org"))
        response = stanza.make_error_response("not-acceptable")
        processor.uplink_receive(response)
        self.assertEqual(len(callback_calls), 0)
        self.assertEqual(len(error_callback_calls), 1)
        stanza = error_callback_calls[0]
        self.assertIsInstance(stanza, Iq)
        self.assertEqual(stanza.stanza_id, response.stanza_id)

    def test_remove_item(self):
        event_queue = Queue()
        settings = XMPPSettings()
        settings["event_queue"] = event_queue
        client = RosterClient(settings)
        processor = Processor([client])
        item1 = RosterItem(JID("item1@example.org"))
        item2 = RosterItem(JID("item2@example.org"))
        client.roster = Roster([item1, item2])

        # simple remove
        client.remove_item(JID("item1@example.org"))
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item1@example.org"))
        self.assertIsNone(item.name)
        self.assertEqual(item.subscription, "remove")
        self.assertFalse(item.approved)
        self.assertFalse(item.groups)
        response = stanza.make_result_response()
        processor.uplink_receive(response)
        self.assertEqual(len(client.roster), 2) # not added yet, push needed

        # missing
        processor.stanzas_sent = []
        with self.assertRaises(KeyError):
            client.remove_item(JID("item3@example.org"))
        self.assertEqual(len(processor.stanzas_sent), 0)

        def callback(item):
            callback_calls.append(item)
        def error_callback(stanza):
            error_callback_calls.append(stanza)

        # callback
        processor.stanzas_sent = []
        callback_calls = []
        error_callback_calls = []
        client.remove_item(JID("item1@example.org"),
                            callback = callback,
                            error_callback = error_callback)
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item1@example.org"))
        response = stanza.make_result_response()
        processor.uplink_receive(response)
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0].jid, JID("item1@example.org"))
        self.assertEqual(len(error_callback_calls), 0)

        # error callback
        processor.stanzas_sent = []
        callback_calls = []
        error_callback_calls = []
        client.remove_item(JID("item1@example.org"),
                            callback = callback,
                            error_callback = error_callback)
        self.assertEqual(len(processor.stanzas_sent), 1)
        stanza = processor.stanzas_sent[0]
        payload = stanza.get_payload(RosterPayload)
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload), 1)
        item = payload[0]
        self.assertEqual(item.jid, JID("item1@example.org"))
        response = stanza.make_error_response("not-acceptable")
        processor.uplink_receive(response)
        self.assertEqual(len(callback_calls), 0)
        self.assertEqual(len(error_callback_calls), 1)
        stanza = error_callback_calls[0]
        self.assertIsInstance(stanza, Iq)
        self.assertEqual(stanza.stanza_id, response.stanza_id)

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
