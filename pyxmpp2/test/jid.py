#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

"""Tests for pyxmpp2.jid"""

import sys
import unittest

import logging

from pyxmpp2.jid import JID, JIDError
from pyxmpp2 import xmppstringprep

logger = logging.getLogger("pyxmpp2.test.jid")

LONG_DOMAIN = (u"x"*60 + ".") * 16 + u"x" * 47
VALID_JIDS = [
    (u"a@b/c",
        (u"a",u"b",u"c")),
    (u"example.com",
        (None, u"example.com",None)),
    (u"example.com/Test",
        (None, u"example.com","Test")),
    (u"jajcus@jajcus.net",
        (u"jajcus",u"jajcus.net",None)),
    (u"jajcus@192.168.1.1",
        (u"jajcus",u"192.168.1.1",None)),
    (u"jajcus@[2001:0DB8::1]",
        (u"jajcus",u"[2001:db8::1]",None)),
    (u"jajcus@[2001:0DB8::192.168.1.1]",
        (u"jajcus",u"[2001:db8::c0a8:101]",None)),
    (u"jajcus@jajcus.net/Test",
        (u"jajcus",u"jajcus.net",u"Test")),
    (u"Jajcus@jaJCus.net/Test",
        (u"jajcus",u"jajcus.net",u"Test")),
    (u"Jajcus@jaJCus.net/test",
        (u"jajcus",u"jajcus.net",u"test")),
    (u"jajcuś@dżabber.example.com/Test",
        (u"jajcuś",u"dżabber.example.com",u"Test")),
    (u"JAJCUŚ@DŻABBER.EXAMPLE.COM/TEST",
        (u"jajcuś",u"dżabber.example.com",u"TEST")),
    (u"%s@%s/%s" % (u"x"*1023, LONG_DOMAIN, u"x"*1023),
        (u"x"*1023, LONG_DOMAIN, u"x"*1023)),
]

VALID_TUPLES = [
    ((u"a",u"b",u"c"), u"a@b/c"),
    ((None, u"example.com",None), u"example.com"),
    ((u"",u"example.com",u""), u"example.com"),
    ((None, u"example.com","Test"), u"example.com/Test"),
    ((u"jajcus",u"jajcus.net",None), u"jajcus@jajcus.net"),
    ((u"jajcus",u"jajcus.net",u"Test"), u"jajcus@jajcus.net/Test"),
    ((u"Jajcus",u"jaJCus.net",u"Test"), u"jajcus@jajcus.net/Test"),
    ((u"Jajcus",u"jaJCus.net",u"test"), u"jajcus@jajcus.net/test"),
    ((u"jajcuś",u"dżabber.example.com",u"Test"),
                                        u"jajcuś@dżabber.example.com/Test"),
    ((u"JAJCUŚ",u"DŻABBER.EXAMPLE.COM",u"TEST"),
                                        u"jajcuś@dżabber.example.com/TEST"),
]

INVALID_JIDS = [
    u"/Test",
    u"#@$%#^$%#^&^$",
    u"<>@example.com",
    u"\x01\x02\x05@example.com",
    u"test@\x01\x02\x05",
    u"test@example.com/\x01\x02\x05",
    u"%s@%s/%s" % (u"x"*1024, u"x"*1023, u"x"*1023),
    u"%s@%s/%s" % (u"x"*1023, u"x"*1024, u"x"*1023),
    u"%s@%s/%s" % (u"x"*1023, u"x"*1023, u"x"*1024),
    u"%só@%s/%s" % (u"x"*1022, u"x"*1023, u"x"*1023),
    u"%s@%só/%s" % (u"x"*1023, u"x"*1022, u"x"*1023),
    u"%s@%s/%só" % (u"x"*1023, u"x"*1023, u"x"*1022),
]

COMPARISIONS_TRUE = [
    'JID(u"a@b.c") == JID(u"a@b.c")',
    'JID(u"a@b.c") == JID(u"A@b.c")',
    'JID(u"a@b.c") != JID(u"b@b.c")',
    'JID(u"a@b.c") < JID(u"b@b.c")',
    'JID(u"b@b.c") > JID(u"a@b.c")',
    'JID(u"a@b.c") > None',
    'JID(u"1@b.c") > None',
    'None < JID(u"1@b.c")',
]

COMPARISIONS_FALSE = [
    'JID(u"a@b.c") != JID(u"a@b.c")',
    'JID(u"a@b.c") != JID(u"A@b.c")',
    'JID(u"a@b.c") == JID(u"b@b.c")',
    'JID(u"a@b.c") > JID(u"b@b.c")',
    'JID(u"b@b.c") < JID(u"a@b.c")',
    'JID(u"a@b.c") < None',
    'JID(u"1@b.c") < None',
    'None > JID(u"1@b.c")',
]

if sys.version_info[0] >= 3:
    COMPARISIONS_TRUE = [e.replace('u"', '"') for e in COMPARISIONS_TRUE]
    COMPARISIONS_FALSE = [e.replace('u"', '"') for e in COMPARISIONS_FALSE]

class TestJID(unittest.TestCase):
    def test_jid_from_string(self):
        for jid, expected_tuple in VALID_JIDS:
            logging.debug(" checking {0!r}...".format(jid))
            jid = JID(jid)
            jtuple = (jid.local, jid.domain, jid.resource)
            self.assertEqual(jtuple, expected_tuple)
    def test_jid_from_tuple(self):
        for (local, domain, resource), jid in VALID_TUPLES:
            logging.debug(" checking {0!r}...".format(jid))
            j = JID(local, domain, resource)
            self.assertEqual(unicode(j), jid)
    def test_invalid_jids(self):
        for jid in INVALID_JIDS:
            logging.debug(" checking {0!r}...".format(jid))
            with self.assertRaises(JIDError):
                jid = JID(jid)
                logging.debug("   got: {0!r}".format(jid))
    def test_comparision(self):
        for expr in COMPARISIONS_TRUE:
            result = eval(expr)
            self.assertTrue(result, 'Expression %r gave: %r' % (expr, result))
        for expr in COMPARISIONS_FALSE:
            result = eval(expr)
            self.assertFalse(result, 'Expression %r gave: %r' % (expr, result))

class TestUncachedJID(TestJID):
    def setUp(self):
        # pylint: disable=W0404,W0212
        import weakref
        JID.cache = weakref.WeakValueDictionary()
        self.saved_stringprep_cache_size = xmppstringprep._stringprep_cache_size
        xmppstringprep.set_stringprep_cache_size(0)
    def tearDown(self):
        xmppstringprep.set_stringprep_cache_size(
                                            self.saved_stringprep_cache_size)

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
