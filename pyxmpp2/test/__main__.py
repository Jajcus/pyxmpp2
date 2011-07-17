"""Startup script for the whole pyxmpp test suite."""

import unittest
import pyxmpp2.test

def load_tests(loader, standard_tests, pattern):
    """Load all tests discovered in pyxmpp2.test."""
    # pylint: disable=W0613
    return pyxmpp2.test.discover()

unittest.main()
