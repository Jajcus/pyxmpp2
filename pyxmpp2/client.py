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

"""Basic XMPP-IM client implementation.

Normative reference:
  - :RFC:`6120`
  - :RFC:`6121` (TODO: roster and presence management)
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import threading
import logging

from .clientstream import ClientStream
from .mainloop import main_loop_factory
from .mainloop.interfaces import EventHandler, event_handler
from .streamevents import DisconnectedEvent
from .transport import TCPTransport
from .settings import XMPPSettings
from .session import SessionHandler
from .streamtls import StreamTLSHandler

logger = logging.getLogger("pyxmpp2.client")

class Client(EventHandler):
    """Base class for an XMPP-IM client.

    Joins the `MainLoop`, `ClientStream` and some basic handlers together,
    so a client application needs only to add its handlers.

    :Ivariables:
        - `jid`: configured JID of the client (current full JID is avialable as
          ``self.stream.jid``).
        - `mainloop`: the main loop object
        - `settings`: configuration settings
        - `handlers`: stream and main loop handlers provided via the
          constructor
        - `stream`: the stream object when connected
        - `lock`: lock protecting the object
        - `_ml_handlers`: list of handlers installed by this object to at the
          main loop
    :Types:
        - `jid`: `jid.JID`
        - `mainloop`: `mainloop.interfaces.MainLoop`
        - `settings`: `XMPPSettings`
        - `stream`: `clientstream.ClientStream`
        - `lock`: :std:`threading.RLock`
    """
    def __init__(self, jid, handlers, settings = None, mainloop = None):
        """Initialize a Client object.

        :Parameters:
            - `jid`: user JID for the connection.
            - `settings`: client settings.
            - `mainloop`: Main event loop to attach to. If None, a loop
              will be created.
        :Types:
            - `jid`: `jid.JID`
            - `settings`: `settings.XMPPSettings`
            - `mainloop`: `mainloop.interfaces.MainLoop`
        """
        self.jid = jid
        self.settings = settings if settings else XMPPSettings()
        self.handlers = handlers
        self._ml_handlers = self.settings["base_client_handlers"]
        self._ml_handlers += list(handlers) + [self]
        if mainloop is not None:
            self.mainloop = mainloop
            for handler in self._ml_handlers:
                self.mainloop.add_handler(handler)
        else:
            self.mainloop = main_loop_factory(settings, self._ml_handlers)
        self.stream = None
        self.lock = threading.RLock()

    def __del__(self):
        for handler in self._ml_handlers:
            self.mainloop.remove_handler(handler)
        self._ml_handlers = []

    def connect(self):
        """Schedule a new XMPP c2s connection.
        """
        with self.lock:
            if self.stream:
                logger.debug("Closing the previously used stream.")
                self._close_stream()

            transport = TCPTransport(self.settings)
            
            addr = self.settings["server"]
            if addr:
                service = None
            else:
                addr = self.jid.domain
                service = self.settings["c2s_service"]

            transport.connect(addr, self.settings["c2s_port"], service)
            handlers = self.settings["base_client_handlers"]
            handlers += self.handlers + [self]
            stream = ClientStream(self.jid, handlers, self.settings)
            stream.initiate(transport)
            self.mainloop.add_handler(transport)
            self.mainloop.add_handler(stream)
            self._ml_handlers += [transport, stream]
            self.stream = stream

    def disconnect(self):
        """Gracefully disconnect from the server."""
        with self.lock:
            if self.stream:
                self.stream.disconnect()

    def close_stream(self):
        """Close the stream immediately.
        """
        with self.lock:
            self._close_stream()

    def _close_stream(self):
        """Same as `close_stream` but with the `lock` acquired.
        """
        self.stream.close()
        if self.stream.transport in self._ml_handlers:
            self._ml_handlers.remove(self.stream.transport)
            self.mainloop.remove_handler(self.stream.transport)
        self.stream = None

    def run(self, timeout = None):
        """Call the main loop.

        Convenience wrapper for ``self.mainloop.loop``
        """
        self.mainloop.loop(timeout)

    @event_handler(DisconnectedEvent)
    def _stream_disconnected(self, event):
        """Handle stream disconnection event.
        """
        with self.lock:
            if event.stream != self.stream:
                return
            if self.stream is not None and event.stream == self.stream:
                if self.stream.transport in self._ml_handlers:
                    self._ml_handlers.remove(self.stream.transport)
                    self.mainloop.remove_handler(self.stream.transport)
                self.stream = None

def base_client_handlers_factory(settings):
    """Build the default value for the :r:`base_client_handlers setting`
    """
    tls_handler = StreamTLSHandler(settings)
    session_handler = SessionHandler(settings)
    return [tls_handler, session_handler]

XMPPSettings.add_setting(u"base_client_handlers", 
    type = "list of handler objects",
    factory = base_client_handlers_factory, 
    default_d = "A `StreamTLSHandler` and a `SessionHandler` instance",
    doc = u"""The basic handlers used by a `Client` object in addition to the
handlers provides in the constructor invocation."""
    )

XMPPSettings.add_setting(u"c2s_port", default = 5222, basic = True,
    type = int, validator = XMPPSettings.get_int_range_validator(1, 65536),
    cmdline_help = "Port number for XMPP client connections",
    doc = """Port number for client to server connections."""
    )

XMPPSettings.add_setting(u"c2s_service", default = "xmpp-client",
    type = unicode,
    cmdline_help = "SRV service name XMPP client connections",
    doc = """SRV service name for client to server connections."""
    )

XMPPSettings.add_setting(u"server", type = unicode, basic = True,
    cmdline_help = "Server address. (Default: use SRV lookup)",
    doc = """Server address to connect to. By default a DNS SRV record look-up
is done for the requested JID domain part and if that fails - 'A' or 'AAAA'
record lookup for the same domain. This setting may be used to force using
a specific server or when SRV look-ups are not available."""
    )

# vi: sts=4 et sw=4
