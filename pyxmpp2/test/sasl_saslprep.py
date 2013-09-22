#!/usr/bin/python -u
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest

from pyxmpp2.exceptions import StringprepError
from pyxmpp2.sasl.saslprep import SASLPREP

class TestSASLprep(unittest.TestCase):
    # pylint: disable=R0903
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

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
