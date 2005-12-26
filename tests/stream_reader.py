#!/usr/bin/python -u
# -*- coding: UTF-8 -*-

import unittest
import libxml2
from pyxmpp import xmlextra
from pyxmpp.jid import JID,JIDError
from pyxmpp import xmppstringprep

def xml_elements_equal(a, b, ignore_level1_cdata = False):
    if a.name!=b.name:
        print "Name mismatch: %r, %r" % (a.name, b.name)
        return False
    try:
        ns1 = a.ns()
    except libxml2.treeError:
        ns1 = None
    try:
        ns2 = b.ns()
    except libxml2.treeError:
        ns2 = None
    if ns1 or ns2:
        if None in (ns1,ns2):
            print "Ns mismatch: %r, %r" % (ns1, ns2)
            return False
        if ns1.content != ns2.content:
            print "Ns mismatch: %r, %r on %r, %r" % (ns1.content, ns2.content, a, b)
            return False

    ap = a.properties
    bp = b.properties
    while 1:
        if (ap, bp) == (None, None):
            break
        if None in (ap, bp):
            return False
        if ap.name != bp.name:
            return False
        if ap.content != bp.content:
            return False
        ap = ap.next
        bp = bp.next

    ac = a.children
    bc = b.children
    while ac != None or bc != None:
        if ignore_level1_cdata:
            if ac and ac.type!='element':
                ac=ac.next
                continue
            if bc and bc.type!='element':
                bc=bc.next
                continue
        if None in (ac, bc):
            return False
        if ac.type != bc.type:
            return False
        if ac.type == 'element':
            if not xml_elements_equal(ac, bc):
                return False
        elif ac.content != bc.content:
            return False
        ac = ac.next
        bc = bc.next
    return True

class EventTemplate:
    def __init__(self, template):
        self.event, offset, xml = template.split(None,2)
        self.offset = int(offset)
        self.xml = libxml2.parseDoc(eval(xml))

    def __del__(self):
        self.xml.freeDoc()

    def match(self, event, node):
        if self.event!=event:
            return False
        if event=="end":
            return True
        if node.type!='element':
            return False
        if not xml_elements_equal(self.xml.getRootElement(),node):
            return False
        return True

    def __repr__(self):
        return "<EventTemplate %r at %r: %r>" % (self.event, self.offset, self.xml.getRootElement().serialize())

class StreamHandler(xmlextra.StreamHandler):
    def __init__(self, test_case):
        self.test_case = test_case
    def stream_start(self, doc):
        self.test_case.event("start", doc.getRootElement())
    def stream_end(self, doc):
        self.test_case.event("end", None)
    def stanza(self, doc, node):
        self.test_case.event("node", node)

expected_events = []
whole_stream = None

def load_expected_events():
    for l in file("data/stream_info.txt"):
        if l.startswith("#"):
            continue
        l=l.strip()
        expected_events.append(EventTemplate(l))

def load_whole_stream():
    global whole_stream
    whole_stream = libxml2.parseFile("data/stream.xml")

class TestStreamReader(unittest.TestCase):
    def setUp(self):
        self.expected_events = list(expected_events)
        self.handler = StreamHandler(self)
        self.reader = xmlextra.StreamReader(self.handler)
        self.file = file("data/stream.xml")
        self.chunk_start = 0
        self.chunk_end = 0
        self.whole_stream = libxml2.newDoc("1.0")

    def tearDown(self):
        del self.handler
        del self.reader
        self.whole_stream.freeDoc()

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
            data=self.file.read(chunk_length)
            if not data:
                break
            self.chunk_end += len(data)
            r=self.reader.feed(data)
            while r:
                r=self.reader.feed()
            if r is None:
                self.event("end", None)
                break
            self.chunk_start = self.chunk_end
        r1 = self.whole_stream.getRootElement()
        r2 = whole_stream.getRootElement()
        if not xml_elements_equal(r1, r2, True):
            self.fail("Whole stream invalid. Got: %r, Expected: %r"
                    % (self.whole_stream.serialize(), whole_stream.serialize()))

    def event(self, event, node):
        expected = self.expected_events.pop(0)
        self.failUnless(event==expected.event, "Got %r, expected %r" % (event, expected.event))
        if expected.offset < self.chunk_start:
            self.fail("Delayed event: %r. Expected at: %i, found at %i:%i"
                    % (event, expected.offset, self.chunk_start, self.chunk_end))
        if expected.offset > self.chunk_end:
            self.fail("Early event: %r. Expected at: %i, found at %i:%i"
                    % (event, expected.offset, self.chunk_start, self.chunk_end))
        if not expected.match(event,node):
            self.fail("Unmatched event. Expected: %r, got: %r;%r"
                    % (expected, event, node.serialize()))
        if event == "start":
            n = node.docCopyNode(self.whole_stream,1)
            self.whole_stream.addChild(n)
            self.whole_stream.setRootElement(n)
        elif event == "node":
            n = node.docCopyNode(self.whole_stream,1)
            r = self.whole_stream.getRootElement()
            r.addChild(n)

def suite():
    load_expected_events()
    load_whole_stream()
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestStreamReader))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
