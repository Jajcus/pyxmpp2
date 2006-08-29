#!/usr/bin/python

import unittest
import sys
import getopt

all_modules=["vcard","jid","disco","imports","cache","stream_reader", "ns_operations",
    "message", "presence", "dataforms", "interface"]

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

    unittest.TextTestRunner(verbosity=verbosity).run(suite())

if __name__ == '__main__':
    main(sys.argv[1:])
# vi: sts=4 et sw=4
