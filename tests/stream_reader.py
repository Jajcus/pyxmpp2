#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
from pyxmpp import xmlextra
from pyxmpp.jid import JID,JIDError
from pyxmpp import xmppstringprep

class EventTemplate:
    def __init__(self, template):
        self.event, self.offset, self.xml = template.split(None,2)
        self.offset = int(self.offset)

    def match(self, event, node):
        if self.event!=event:
            return False
        if node.type!='element':
            return False
        if self.xml!=`node.serialize()`:
            return False
        return True
            
    def __repr__(self):
        return "<EventTemplate %r at %r: %s>" % (self.event, self.offset, self.xml)

class StreamHandler(xmlextra.StreamHandler):
    def __init__(self, test_case):
        self.test_case = test_case
    def stream_start(self, doc):
        self.test_case.event("start", doc.getRootElement())
    def stream_end(self, doc):
        self.test_case.event("end", doc.getRootElement())
    def stanza(self, doc, node):
        self.test_case.event("node", node)
    def stanza_end(self, doc, node):
        self.test_case.event("node", node)

expected_events = []

def load_expected_events():
    for l in file("data/stream_info.txt"):
        if l.startswith("#"):
            continue
        l=l.strip()
        expected_events.append(EventTemplate(l))

class TestStreamReader(unittest.TestCase):
    def setUp(self):
        self.expected_events = list(expected_events)
        self.handler = StreamHandler(self)
        self.reader = xmlextra.StreamReader(self.handler)
        self.file = file("data/stream.xml")
        self.chunk_start = 0
        self.chunk_end = 0
        
    def test_1(self):
        return self.do_test(1)
        
    def test_2(self):
        return self.do_test(2)
        
    def test_10(self):
        return self.do_test(10)
        
    def test_100(self):
        return self.do_test(100)
        
    def test_1000(self):
        return self.do_test(1000)
        
    def do_test(self, chunk_length):
        while 1:
            data=self.file.read(chunk_length)
            if not data:
                break
            self.chunk_end += len(data)
            self.reader.feed(data)
            self.chunk_start = self.chunk_end

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
        
def suite():
    load_expected_events()
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestStreamReader))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4 encoding=utf-8
