import unittest
import pyxmpp2.test

def load_tests(loader, standard_tests, pattern):
    return pyxmpp2.test.discover()

if __name__ == "__main__":
    unittest.main()
