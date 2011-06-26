#
# (C) Copyright 2003-2010 Jacek Konieczny <jajcus@jajcus.net>
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
  - :RFC:`6121` (TODO)
"""

from __future__ import absolute_import

__docformat__="restructuredtext en"

import threading
import logging

from .clientstream import ClientStream
from .mainloop import main_loop_factory
from .mainloop.interfaces import EventHandler, event_handler
from .streamevents import DisconnectedEvent
from .transport import TCPTransport
from .settings import XMPPSettings
from .session import SessionHandler

logger = logging.getLogger("pyxmpp.client")

def base_client_handlers_factory(settings):
    session_handler = SessionHandler(settings)
    return [session_handler]

XMPPSettings.add_default_factory("base_client_handlers",
                                                base_client_handlers_factory)


class Client(EventHandler):
    """Base class for an XMPP-IM client.

    :Ivariables:
        - `jid`: configured JID of the client (current full JID is avialable as
          `self.stream.jid`).
        - `mainloop`: the main loop object
    :Types:
        - `jid`: `jid.JID`
        - `mainloop`: `mainloop.interfaces.MainLoop`
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
            transport.connect(self.jid.domain, self.settings["client_port"],
                                            self.settings["client_service"])
            stream = ClientStream(self.jid, self.handlers, self.settings)
            stream.initiate(transport)
            self.mainloop.add_handler(transport)
            self.mainloop.add_handler(stream)
            self._ml_handlers += [transport, stream]
            self.stream = stream

    def disconnect(self):
        """Gracefully disconnect from the server."""
        with self.lock:
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

XMPPSettings.add_defaults({
                            u"client_port": 5222, 
                            u"client_service": "xmpp-client", 
                            })


# vi: sts=4 et sw=4
