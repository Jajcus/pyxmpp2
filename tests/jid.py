#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
from pyxmpp2.jid import JID,JIDError
from pyxmpp2 import xmppstringprep

valid_jids=[
    (u"a@b/c",
        (u"a",u"b",u"c")),
    (u"example.com",
        (None,u"example.com",None)),
    (u"example.com/Test",
        (None,u"example.com","Test")),
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
    (u"%s@%s/%s" % (u"x"*1023,u"x"*1023,u"x"*1023),
        (u"x"*1023,u"x"*1023,u"x"*1023)),
]

valid_tuples=[
    ((u"a",u"b",u"c"),u"a@b/c"),
    ((None,u"example.com",None),u"example.com"),
    ((u"",u"example.com",u""),u"example.com"),
    ((None,u"example.com","Test"),u"example.com/Test"),
    ((u"jajcus",u"jajcus.net",None),u"jajcus@jajcus.net"),
    ((u"jajcus",u"jajcus.net",u"Test"),u"jajcus@jajcus.net/Test"),
    ((u"Jajcus",u"jaJCus.net",u"Test"),u"jajcus@jajcus.net/Test"),
    ((u"Jajcus",u"jaJCus.net",u"test"),u"jajcus@jajcus.net/test"),
    ((u"jajcuś",u"dżabber.example.com",u"Test"),u"jajcuś@dżabber.example.com/Test"),
    ((u"JAJCUŚ",u"DŻABBER.EXAMPLE.COM",u"TEST"),u"jajcuś@dżabber.example.com/TEST"),
]

invalid_jids=[
    u"/Test",
    u"#@$%#^$%#^&^$",
    u"<>@example.com",
    u"test@example.com/(&*&^%$#@@!#",
    u"\01\02\05@example.com",
    u"test@\01\02\05",
    u"test@example.com/\01\02\05",
    u"%s@%s/%s" % (u"x"*1024,u"x"*1023,u"x"*1023),
    u"%s@%s/%s" % (u"x"*1023,u"x"*1024,u"x"*1023),
    u"%s@%s/%s" % (u"x"*1023,u"x"*1023,u"x"*1024),
    u"%só@%s/%s" % (u"x"*1022,u"x"*1023,u"x"*1023),
    u"%s@%só/%s" % (u"x"*1023,u"x"*1022,u"x"*1023),
    u"%s@%s/%só" % (u"x"*1023,u"x"*1023,u"x"*1022),
]

comparisions_true=[
    'JID(u"a@b.c") == JID(u"a@b.c")',
    'JID(u"a@b.c") == JID(u"A@b.c")',
    'JID(u"a@b.c") != JID(u"b@b.c")',
    'JID(u"a@b.c") < JID(u"b@b.c")',
    'JID(u"b@b.c") > JID(u"a@b.c")',
    'JID(u"a@b.c") > None',
    'JID(u"1@b.c") > None',
    'None < JID(u"1@b.c")',
]

comparisions_false=[
    'JID(u"a@b.c") != JID(u"a@b.c")',
    'JID(u"a@b.c") != JID(u"A@b.c")',
    'JID(u"a@b.c") == JID(u"b@b.c")',
    'JID(u"a@b.c") > JID(u"b@b.c")',
    'JID(u"b@b.c") < JID(u"a@b.c")',
    'JID(u"a@b.c") < None',
    'JID(u"1@b.c") < None',
    'None > JID(u"1@b.c")',
]

class TestJID(unittest.TestCase):
    def test_jid_from_string(self):
        for jid,tuple in valid_jids:
            j=JID(jid)
            jtuple=(j.local,j.domain,j.resource)
            self.assertEqual(jtuple,tuple)
    def test_jid_from_tuple(self):
        for (local,domain,resource),jid in valid_tuples:
            j=JID(local,domain,resource)
            self.assertEqual(unicode(j),jid)
    def test_invalid_jids(self):
        for jid in invalid_jids:
            try:
                j=JID(jid)
            except JIDError,e:
                return
            except Exception,e:
                raise
            self.fail("Invalid JID passed: %r -> %r" % (jid,j))
    def test_comparision(self):
        for e in comparisions_true:
            result=eval(e)
            self.assertTrue(result,'Expression %r gave: %r' % (e,result))
        for e in comparisions_false:
            result=eval(e)
            self.assertFalse(result,'Expression %r gave: %r' % (e,result))

class TestUncachedJID(TestJID):
    def setUp(self):
        import weakref
        JID.cache=weakref.WeakValueDictionary()
        self.saved_stringprep_cache_size = xmppstringprep._stringprep_cache_size
        xmppstringprep.set_stringprep_cache_size(0)
    def tearDown(self):
        xmppstringprep.set_stringprep_cache_size(self.saved_stringprep_cache_size)

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestUncachedJID))
     suite.addTest(unittest.makeSuite(TestJID))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
