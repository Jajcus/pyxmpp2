#!/usr/bin/python -u
#
# A simple message-sending script

import sys

from pyxmpp.jid import JID
from pyxmpp.jabber.simple import send_message

if len(sys.argv)!=6:
    print u"Usage:"
    print "\t%s my_jid my_password recipient_jid subject body" % (sys.argv[0],)
    print "example:"
    print "\t%s test@localhost verysecret test1@localhost Test 'this is test'" % (sys.argv[0],)
    sys.exit(1)

jid,password,recpt,subject,body=sys.argv[1:]
jid=JID(jid)
if not jid.resource:
    jid=JID(jid.node,jid.domain,"send_message")
recpt=JID(recpt)
send_message(jid,password,recpt,body,subject)
# vi: sts=4 et sw=4
