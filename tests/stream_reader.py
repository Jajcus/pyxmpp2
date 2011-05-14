#!/usr/bin/python -u
# -*- coding: UTF-8 -*-

import sys

import unittest
from xml.etree import ElementTree

from pyxmpp2 import xmppparser
from pyxmpp2.jid import JID, JIDError
from pyxmpp2 import xmppstringprep

from pyxmpp2.utils import xml_elements_equal

class EventTemplate:
    def __init__(self, template):
        self.event, offset, xml = template.split(None,2)
        self.offset = int(offset)
        self.xml = ElementTree.XML(eval(xml))

    def match(self, event, node):
        if self.event != event:
            return False
        if event == "end":
            return True
        if not xml_elements_equal(self.xml, node):
            return False
        return True

    def __repr__(self):
        return "<EventTemplate %r at %r: %r>" % (self.event, self.offset, ElementTree.dump(self.xml))

class StreamHandler(xmppparser.StreamHandler):
    def __init__(self, test_case):
        self.test_case = test_case
    def stream_start(self, element):
        self.test_case.event("start", element)
    def stream_end(self, element):
        self.test_case.event("end", None)
    def stanza(self, element):
        self.test_case.event("node", element)

expected_events = []
whole_stream = None

def load_expected_events():
    for l in file("data/stream_info.txt"):
        if l.startswith("#"):
            continue
        l = l.strip()
        expected_events.append(EventTemplate(l))

def load_whole_stream():
    global whole_stream
    whole_stream = ElementTree.parse("data/stream.xml")

class TestStreamReader(unittest.TestCase):
    def setUp(self):
        self.expected_events = list(expected_events)
        self.handler = StreamHandler(self)
        self.reader = xmppparser.StreamReader(self.handler)
        self.file = file("data/stream.xml")
        self.chunk_start = 0
        self.chunk_end = 0
        self.whole_stream = ElementTree.ElementTree()

    def tearDown(self):
        del self.handler
        del self.reader
        del self.whole_stream

    def test_1(self):
        self.do_test(1)

    def test_2(self):
        self.do_test(2)

    def test_10(self):
        self.do_test(10)

    def test_100(self):
        self.do_test(100)

    def test_1000(self):
        self.do_test(1000)

    def do_test(self, chunk_length):
        while 1:
            data = self.file.read(chunk_length)
            if not data:
                break
            self.chunk_end += len(data)
            self.reader.feed(data)
            if not data:
                self.event("end", None)
                break
            self.chunk_start = self.chunk_end
        r1 = self.whole_stream.getroot()
        r2 = whole_stream.getroot()
        if not xml_elements_equal(r1, r2, True):
            self.fail("Whole stream invalid. Got: %r, Expected: %r"
                    % (ElementTree.tostring(r1), ElementTree.tostring(r2)))

    def event(self, event, element):
        expected = self.expected_events.pop(0)
        self.failUnless(event==expected.event, "Got %r, expected %r" % (event, expected.event))
        if expected.offset < self.chunk_start:
            self.fail("Delayed event: %r. Expected at: %i, found at %i:%i"
                    % (event, expected.offset, self.chunk_start, self.chunk_end))
        if expected.offset > self.chunk_end:
            self.fail("Early event: %r. Expected at: %i, found at %i:%i"
                    % (event, expected.offset, self.chunk_start, self.chunk_end))
        if not expected.match(event,element):
            self.fail("Unmatched event. Expected: %r, got: %r;%r"
                    % (expected, event, ElementTree.dump(element)))
        if event == "start":
            self.whole_stream._setroot(element)
        elif event == "node":
            r = self.whole_stream.getroot()
            r.append(element)

def suite():
    load_expected_events()
    load_whole_stream()
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestStreamReader))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
