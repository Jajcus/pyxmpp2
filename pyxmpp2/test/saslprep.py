#!/usr/bin/python -u
# -*- coding: UTF-8 -*-

import unittest

import re

from pyxmpp2.exceptions import StringprepError
from pyxmpp2.sasl.saslprep import SASLPREP        

class TestSASLprep(unittest.TestCase):
    def test_rfc_examples(self):
        for input_, output in (
                                (u"I\u00ADX",   u"IX"),
                                (u"user",       u"user"),
                                (u"USER",       u"USER"),
                                (u"\u00AA",     u"a"),
                                (u"\u2168",     u"IX"),
                                ):
            result = SASLPREP.prepare(input_)
            self.assertEqual(result, output)
        for input_ in (u"\u0007", u"\u0627\u0031"):
            with self.assertRaises(StringprepError):
                SASLPREP.prepare(input_)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSASLprep))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
