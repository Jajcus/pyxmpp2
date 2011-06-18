#
# (C) Copyright 2011 Jacek Konieczny <jajcus@jajcus.net>
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

"""I/O Handling classes

This module has a purpose similar to `asyncore` from the base library, but
should be more usable, especially for PyXMPP.

Also, these interfaces should allow building application not only in
asynchronous event loop model, but also threaded model.
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import time
import select
import logging

from .events import QUIT
from .base import MainLoopBase

logger = logging.getLogger("pyxmpp.mainloop.select")

class SelectMainLoop(MainLoopBase):
    """Main event loop implementation based on the `select.select()` call."""
    def __init__(self, handlers = []):
        self._handlers = []
        self._prepared = set()
        self._timeout_handlers = []
        MainLoopBase.__init__(self, handlers)

    def add_io_handler(self, handler):
        """Add an I/O handler to the loop."""
        self._handlers.append(handler)
        handler.set_event_queue(self.event_queue)

    def update_io_handler(self, handler):
        """Add an I/O handler to the loop."""
        if handler in self._handlers:
            return
        else:
            raise KeyError("Handler")

    def remove_io_handler(self, handler):
        self._handlers.remove(handler)

    def add_timeout_handler(self, timeout, handler):
        """Add a function to be called after `timeout` seconds."""
        self._timeout_handlers.append(timeout, handler)
        self._timeout_handlers.sort(key = lambda x: x[0])

    def loop_iteration(self, timeout = 60):
        """A loop iteration - check any scheduled events
        and I/O available and run the handlers.
        """
        if self.event_queue.flush() is QUIT:
            self._quit = True
            return 0
        sources_handled = 0
        now = time.time()
        schedule = None
        while self._timeout_handlers:
            schedule, handler = self._timeout_handlers[0]
            if schedule <= now:
                self._timeout_handlers = self._timeout_handlers[1:]
                handler()
                sources_handled += 1
            if self.event_queue.flush() is QUIT:
                self._quit = True
                return sources_handled
        if self._timeout_handlers and schedule:
            timeout = min(timeout, schedule - now)
        readable = []
        writable = []
        for handler in self._handlers:
            if handler not in self._prepared:
                logger.debug(" preparing handler: {0!r}".format(handler))
                ret = handler.prepare()
                logger.debug("   prepare result: {0!r}".format(ret))
                if isinstance(ret, HandlerReady):
                    self._prepared.add(handler)
                elif isinstance(ret, PrepareAgain):
                    if ret.timeout is not None:
                        timeout = min(timeout, ret.timeout)
                else:
                    raise TypeError("Unexpected result type from prepare()")
            if not handler.fileno():
                continue
            if handler.is_readable():
                logger.debug(" {0!r} readable".format(handler))
                readable.append(handler)
            if handler.is_writable():
                logger.debug(" {0!r} writable".format(handler))
                writable.append(handler)
        if not readable and not writable:
            readable, writable, _unused = [], [], None
            time.sleep(timeout)
        else:
            readable, writable, _unused = select.select(
                                            readable, writable, [], timeout)
        for handler in readable:
            handler.handle_read()
            sources_handled += 1
        for handler in writable:
            handler.handle_write()
            sources_handled += 1
        return sources_handled
