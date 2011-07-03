#!/usr/bin/python

import unittest
import sys
import getopt
import logging

import os

import pyxmpp2.etree
if "PYXMPP2_ETREE" not in os.environ:
    # one of tests fails when xml.etree.ElementTree is used
    import xml.etree.cElementTree
    pyxmpp2.etree.ElementTree = xml.etree.cElementTree


all_modules=[ "jid", "stream_reader", "xmppserializer", "stanza",
            "message", "presence", "iq", "stanzaprocessor",
            "streambase", "sasl_gsasl", "binding", "streamsasl",
            "streamtls", "ext_version",
#             "cache", 
#          "vcard", "disco", "dataforms", "interface"
                ]

def suite(modules=None):
     if not modules:
        modules=all_modules
     suite = unittest.TestSuite()
     for mname in modules:
        mod=__import__(mname)
        suite.addTest(mod.suite())
     return suite

def usage():
    print "Usage:"
    print "  %s [-v <verbosity>] " % (sys.argv[0],)
    print "  %s -h"

def main(args=None):
    verbosity=1
    if args:
        try:
            optlist, modules = getopt.getopt(args, 'v:h')
        except getopt.GetoptError:
            usage()
            sys.exit(2)
        for o,v in optlist:
            if o=='-v':
                verbosity=int(v)
            elif o=='-h':
                usage()
                sys.exit(0)
    else:
        modules=None
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    if verbosity > 2:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.ERROR)
    unittest.TextTestRunner(verbosity=verbosity).run(suite())

if __name__ == '__main__':
    main(sys.argv[1:])

# vi: sts=4 et sw=4
