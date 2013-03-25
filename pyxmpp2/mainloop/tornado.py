#
# (C) Copyright 2012 lilydjwg <lilydjwg@gmail.com>
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

"""Tornado main loop integration."""

from __future__ import absolute_import, division

import logging
from functools import partial
import inspect
import time

from tornado import ioloop
from .interfaces import HandlerReady, PrepareAgain, QUIT
from .base import MainLoopBase

logger = logging.getLogger(__name__)

class TornadoMainLoop(MainLoopBase):
    """Main event loop based on Tornado's ioloop."""

    def __init__(self, settings = None, handlers = None, io_loop=None):
        self._handlers = {}
        self._unprepared_handlers = {}
        self.io_loop = io_loop or ioloop.IOLoop.instance()
        MainLoopBase.__init__(self, settings, handlers)

    def _add_io_handler(self, handler):
        """Add an I/O handler to the loop."""
        logger.debug('adding io handler: %r', handler)
        self._unprepared_handlers[handler] = None
        self._configure_io_handler(handler)

    def _configure_io_handler(self, handler):
        """Register an io-handler at the polling object."""
        if self.check_events():
            return
        if handler in self._unprepared_handlers:
            old_fileno = self._unprepared_handlers[handler]
            prepared = self._prepare_io_handler(handler)
        else:
            old_fileno = None
            prepared = True
        fileno = handler.fileno()
        if old_fileno is not None and fileno != old_fileno:
            del self._handlers[old_fileno]
            # remove_handler won't raise something like KeyError if the fd
            # isn't registered; it will just print a debug log.
            self.io_loop.remove_handler(old_fileno)
        if not prepared:
            self._unprepared_handlers[handler] = fileno
        if not fileno:
            return
        update = fileno in self._handlers
        events = ioloop.IOLoop.NONE
        if handler.is_readable():
            logger.debug(" {0!r} readable".format(handler))
            events |= ioloop.IOLoop.READ
        if handler.is_writable():
            logger.debug(" {0!r} writable".format(handler))
            events |= ioloop.IOLoop.WRITE

        if self._handlers.get(fileno, None) == events:
            return
        self._handlers[fileno] = events
        if events:
            logger.debug(" registering {0!r} handler fileno {1} for"
                            " events {2}".format(handler, fileno, events))
            if update:
                self.io_loop.update_handler(fileno, events)
            else:
                self.io_loop.add_handler(
                    fileno, partial(self._handle_event, handler), events
                )

    def _prepare_io_handler(self, handler):
        """Call the `interfaces.IOHandler.prepare` method and
        remove the handler from unprepared handler list when done.
        """
        logger.debug(" preparing handler: {0!r}".format(handler))
        ret = handler.prepare()
        logger.debug("   prepare result: {0!r}".format(ret))
        if isinstance(ret, HandlerReady):
            del self._unprepared_handlers[handler]
            prepared = True
        elif isinstance(ret, PrepareAgain):
            if ret.timeout is not None:
                now = time.time()
                self.io_loop.add_timeout(
                    now + ret.timeout,
                    partial(self._configure_io_handler, handler)
                )
            else:
                self.io_loop.add_callback(
                    partial(self._configure_io_handler, handler)
                )
            prepared = False
        else:
            raise TypeError("Unexpected result type from prepare()")
        return prepared

    def _remove_io_handler(self, handler):
        """Remove an i/o-handler."""
        if handler in self._unprepared_handlers:
            old_fileno = self._unprepared_handlers[handler]
            del self._unprepared_handlers[handler]
        else:
            old_fileno = handler.fileno()
        if old_fileno is not None:
            del self._handlers[old_fileno]
            self.io_loop.remove_handler(handler.fileno())

    def _add_timeout_handler(self, handler):
        logger.debug('adding timeout handler: %r', handler)
        now = time.time()
        for dummy, method in inspect.getmembers(handler, callable):
            if not hasattr(method, "_pyxmpp_timeout"):
                continue
            # pylint: disable=W0212
            logger.debug(" registering {0!r} handler with timeout {1}".format(
                handler, method._pyxmpp_timeout))
            handler._tornado_timeout = self.io_loop.add_timeout(
                now + method._pyxmpp_timeout, method
            )

    def _remove_timeout_handler(self, handler):
        for dummy, method in inspect.getmembers(handler, callable):
            if not hasattr(method, "_tornado_timeout"):
                continue
            # pylint: disable=W0212
            self.io_loop.remove_timeout(method._tornado_timeout)

    def quit(self):
        self._quit = True
        self.io_loop.stop()

    def loop(self, timeout=None):
        logger.debug('looping, timeout is %r', timeout)
        if timeout is not None:
            now = time.time()
            self.io_loop.add_timeout(now + timeout, self.quit)
        self.io_loop.start()

    def loop_iteration(self, timeout=1):
        pass

    def check_events(self):
        if self.event_dispatcher.flush() is QUIT:
            self.quit()
            return True
        return False

    def _handle_event(self, handler, fd, event):
        """handle I/O events"""
        # pylint: disable=C0103
        logger.debug('_handle_event: %r, %r, %r', handler, fd, event)
        if event & ioloop.IOLoop.ERROR:
            handler.handle_hup()
        if event & ioloop.IOLoop.READ:
            handler.handle_read()
        if event & ioloop.IOLoop.WRITE:
            handler.handle_write()
        self._configure_io_handler(handler)
