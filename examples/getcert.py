#!/usr/bin/python -u
#
# This example fetches server certificate
#

import sys
import logging
import locale
import codecs
import ssl

from pyxmpp.jabber.client import JabberClient
from pyxmpp.streamtls import TLSSettings
from pyxmpp.jid import JID

class Client(JabberClient):
    """Simple client which extracts server certificate."""
    def __init__(self, server_jid):
        jid = JID("dummy", server_jid.domain, "GetCert")

        tls_settings = TLSSettings(require = True, verify_peer = False)

        # setup client with provided connection information
        # and identity data
        JabberClient.__init__(self, jid, "",
                disco_name="PyXMPP example: getcert.py", disco_type="bot",
                tls_settings = tls_settings)

    def stream_state_changed(self, state, arg):
        """This one is called when the state of stream connecting the component
        to a server changes. This will usually be used to let the user
        know what is going on."""
        if state == 'fully connected':
            self.disconnect()
        if state != 'tls connected':
            return
        cert = self.stream.tls.getpeercert(True)
        pem_cert = ssl.DER_cert_to_PEM_cert(cert).strip()
        if pem_cert[-len(ssl.PEM_FOOTER)-1:len(ssl.PEM_FOOTER)] != '\n':
            # Python 2.6.4 but workaround
            pem_cert = pem_cert[:-len(ssl.PEM_FOOTER)] + "\n" + ssl.PEM_FOOTER
        print pem_cert

# XMPP protocol is Unicode-based to properly display data received
# _must_ convert it to local encoding or UnicodeException may be raised
locale.setlocale(locale.LC_CTYPE, "")
encoding = locale.getlocale()[1]
if not encoding:
    encoding = "us-ascii"
sys.stdout = codecs.getwriter(encoding)(sys.stdout, errors = "replace")
sys.stderr = codecs.getwriter(encoding)(sys.stderr, errors = "replace")

# PyXMPP uses `logging` module for its debug output
# applications should set it up as needed
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR) # change to DEBUG for higher verbosity

if len(sys.argv) != 2:
    print u"Usage:"
    print "\t%s domain" % (sys.argv[0],)
    print "example:"
    print "\t%s jabber.org" % (sys.argv[0],)
    sys.exit(1)

c=Client(JID(sys.argv[1]))
c.connect()
try:
    c.loop(1)
except KeyboardInterrupt:
    c.disconnect()

# vi: sts=4 et sw=4
