#
# (C) Copyright 2003-2011 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# pylint: disable-msg=W0221

"""Client-Server stream handling.

Normative reference:
  - `RFC 6120 <http://www.ietf.org/rfc/rfc6120.txt>`__
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import logging

from .streambase import StreamBase
from .jid import JID
from .exceptions import StreamError,StreamAuthenticationError,FatalStreamError
from .exceptions import ClientStreamError, FatalClientStreamError

def base_c2s_handlers_factory(settings):
    sasl_handler = StreamSASLHandler(settings)
    binding_handler = ResourceBindingHandler(settings)
    return [sasl_handler, binding_handler]

XMPPSettings.add_default_factory("base_c2s_handlers",
                                                    base_c2s_handlers_factory)

class ClientStream(StreamBase):
    """Handles XMPP-IM c2s stream.

    Both client and server side of the connection is supported. This class
    handles client SASL authentication, authorisation and resource binding.
    """
    def __init__(self, jid, handlers, settings = None):
        """Initialize the ClientStream object.

        :Parameters:
            - `jid`: local JID.
            - `handlers`: XMPP feature and event handlers
            - `settings`: PyXMPP settings for the stream
        :Types:
            - `jid`: `JID`
            - `settings`: `XMPPSettings`
        """
        if handlers is None:
            handlers = []
        if settings is None:
            settings = TLSSettings()
        self.me = JID(jid.local, jid.domain)
        if "resource" not in settings:
            settings["resource"] = jid.resource
        handlers = handlers + settings["base_c2s_handlers"]
        StreamBase.__init__(STANZA_CLIENT_NS, handlers, settings)
    
    def connect(self, addr = None, port = 5222, service = "xmpp-client",
                                                                    to = None):
        """Establish XMPP connection with given address.

        [initiating entity only]

        :Parameters:
            - `addr`: peer name or IP address
            - `port`: port number to connect to
            - `service`: service name (to be resolved using SRV DNS records)
            - `to`: peer name if different than `addr`
        """
        if addr is None:
            addr = self.jid.domain
        return StreamBase.connect(self, addr, port, service, to)

    def accept(self, sock, myname = None):
        """Accept an incoming client connection.

        [server only]

        :Parameters:
            - `sock`: a listening socket.
            - `myname`: local stream endpoint name.
        """
        if myname is None:
            myname = self.me.domain
        StreamBase.accept(self, sock, myname)

    def fix_out_stanza(self, stanza):
        """Fix outgoing stanza.

        On a client clear the sender JID. On a server set the sender
        address to the own JID if the address is not set yet."""
        StreamBase.fix_out_stanza(self, stanza)
        if self.initiator:
            if stanza.from_jid:
                stanza.from_jid = None
        else:
            if not stanza.from_jid:
                stanza.from_jid = self.my_jid

    def fix_in_stanza(self, stanza):
        """Fix an incoming stanza.

        Ona server replace the sender address with authorized client JID."""
        StreamBase.fix_in_stanza(self, stanza)
        if not self.initiator:
            if stanza.from_jid != self.peer:
                stanza.set_from(self.peer)

# vi: sts=4 et sw=4
