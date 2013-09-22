#!/usr/bin/python -u
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import os
import logging

from pyxmpp2.test._support import DATA_DIR

logger = logging.getLogger("pyxmpp2.test.stream_reader")

import unittest
from xml.etree import ElementTree

from pyxmpp2 import xmppparser

from pyxmpp2.utils import xml_elements_equal

class EventTemplate:
    # pylint: disable=R0903
    def __init__(self, template):
        self.event, offset, xml = template.split(None, 2)
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
        return "<EventTemplate %r at %r: %r>" % (self.event, self.offset,
                                                    ElementTree.dump(self.xml))

class StreamHandler(xmppparser.XMLStreamHandler):
    def __init__(self, test_case):
        xmppparser.XMLStreamHandler.__init__(self)
        self.test_case = test_case
    def stream_start(self, element):
        self.test_case.event("start", element)
    def stream_end(self):
        self.test_case.event("end", None)
    def stream_element(self, element):
        self.test_case.event("node", element)

# pylint: disable=C0103
expected_events = []
# pylint: disable=C0103
whole_stream = None

def load_expected_events():
    with open(os.path.join(DATA_DIR, "stream_info.txt")) as stream_info:
        for line in stream_info:
            if line.startswith("#"):
                continue
            line = line.strip()
            expected_events.append(EventTemplate(line))

def load_whole_stream():
    # pylint: disable=W0603
    global whole_stream
    whole_stream = ElementTree.parse(os.path.join(DATA_DIR, "stream.xml"))

class TestStreamReader(unittest.TestCase):
    def setUp(self):
        self.expected_events = list(expected_events)
        self.handler = StreamHandler(self)
        self.reader = xmppparser.StreamReader(self.handler)
        self.file = open(os.path.join(DATA_DIR, "stream.xml"))
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
                self.reader.feed('')
                break
            self.chunk_end += len(data)
            self.reader.feed(data)
            if not data:
                self.event("end", None)
                break
            self.chunk_start = self.chunk_end
        root1 = self.whole_stream.getroot()
        self.assertIsNotNone(root1)
        root2 = whole_stream.getroot()
        if not xml_elements_equal(root1, root2, True):
            self.fail("Whole stream invalid. Got: %r, Expected: %r"
                                    % (ElementTree.tostring(root1),
                                                ElementTree.tostring(root2)))

    def event(self, event, element):
        logger.debug(" event: {0!r} element: {1!r}".format(event, element))
        expected = self.expected_events.pop(0)
        self.assertTrue(event==expected.event, "Got %r, expected %r" %
                                                    (event, expected.event))
        if expected.offset < self.chunk_start:
            self.fail("Delayed event: %r. Expected at: %i, found at %i:%i"
                    % (event, expected.offset, self.chunk_start,
                                                            self.chunk_end))
        if expected.offset > self.chunk_end:
            self.fail("Early event: %r. Expected at: %i, found at %i:%i"
                    % (event, expected.offset, self.chunk_start,
                                                            self.chunk_end))
        if not expected.match(event, element):
            self.fail("Unmatched event. Expected: %r, got: %r;%r"
                    % (expected, event, ElementTree.dump(element)))
        if event == "start":
            # pylint: disable=W0212
            self.whole_stream._setroot(element)
        elif event == "node":
            root = self.whole_stream.getroot()
            root.append(element)

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    load_expected_events()
    load_whole_stream()
    setup_logging()

if __name__ == "__main__":
    unittest.main()
