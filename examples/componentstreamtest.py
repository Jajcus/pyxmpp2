#!/usr/bin/python -u

import sys
import logging

from pyxmpp import JID
from pyxmpp.jabberd import ComponentStream

logger=logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

class Stream(ComponentStream):
    def state_change(self,state,arg):
        print "*** State changed: %s %r ***" % (state,arg)

if len(sys.argv)<5:
    print "Usage:"
    print "\t%s name secret server port" % (sys.argv[0])
    sys.exit(1)

print "creating stream..."
s=Stream(JID(sys.argv[1]),sys.argv[2],sys.argv[3],int(sys.argv[4]))

print "connecting..."
s.connect()

print "looping..."
try:
    s.loop(1)
except KeyboardInterrupt:
    s.close()
    pass

print "exiting..."
# vi: sts=4 et sw=4
