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
import threading

from abc import ABCMeta

class IOHandler:
    """Wrapper for a socket or a file descriptor to be used in event loop
    or for I/O threads."""
    # pylint: disable-msg=W0232,R0921
    __metaclass__ = ABCMeta
    def fileno(self):
        """Return file descriptor to poll or select."""
        raise NotImplementedError
    def setblocking(self, blocking = True):
        """Force the handler into blocking or nonblocking mode, so the
        `handle_write()` and `handle_read()` methods are guaranteed to block
        for some time (or fail if not `readable()` or `writable()` if nothing
        can be written or there is nothing to read."""
        raise NotImplementedError
    def readable(self):
        """
        :Return: `True` when the I/O channel can be read
        """
        raise NotImplementedError
    def wait_for_readability(self):
        """
        Stop current thread until the channel is readable.

        :Return: `False` if it won't be readable (e.g. is closed)
        """
        raise NotImplementedError
    def writable(self):
        """
        :Return: `True` when the I/O channel can be written to
        """
        raise NotImplementedError
    def volatile(self):
        """
        :Return: `True` if `fileno` result may change
        """
        raise NotImplementedError
    def wait_for_writability(self):
        """
        Stop current thread until the channel is writable.

        :Return: `False` if it won't be readable (e.g. is closed)
        """
        raise NotImplementedError
    def handle_write(self):
        """
        Handle the 'channel writable' state. E.g. send buffered data via a
        socket.
        """
        raise NotImplementedError
    def handle_read(self):
        """
        Handle the 'channel readable' state. E.g. read from a socket.
        """
        raise NotImplementedError
    def handle_hup(self):
        """
        Handle the 'channel hungup' state. The handler should not be writtable
        after this.
        """
        raise NotImplementedError
    def handle_err(self):
        """
        Handle an error reported.
        """
        raise NotImplementedError
    def handle_nval(self):
        """
        Handle an 'invalid file descriptor' event.
        """
        raise NotImplementedError
    def close(self):
        """Close the channell immediately, so it won't expect more events."""
        raise NotImplementedError

class MainLoopBase(object):
    """Base class for main loop implementations.
    """
    _quit = False
    def add_io_handler(self, handler):
        """Add an I/O handler to the loop."""
        raise NotImplementedError
    def update_io_handler(self, handler):
        """Add an I/O handler to the loop."""
        raise NotImplementedError
    def remove_io_handler(self, handler):
        """Remove an I/O handler to the loop."""
        raise NotImplementedError
    def add_timeout_handler(self, timeout, handler):
        """Add a function to be called after `timeout` seconds."""
        raise NotImplementedError
    def quit(self):
        """Make the loop stop after the current iteration."""
        self._quit = True
    def run(self, timeout = 60):
        """Run the loop."""
        while not self._quit:
            self.loop_iteration(timeout)
    def loop_iteration(self, timeout = 60):
        """Single loop iteration."""
        raise NotImplementedError

class SelectMainLoop(MainLoopBase):
    """Main event loop implementation based on the `select.select()` call."""
    def __init__(self):
        MainLoopBase.__init__(self)
        self._quit = False
        self._handlers = []
        self.poll = select.poll()
        self._timeout_handlers = []

    def add_io_handler(self, handler):
        """Add an I/O handler to the loop."""
        self._handlers.append(handler)

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
        sources_handled = 0
        now = time.time()
        schedule = None
        while self._timeout_handlers:
            schedule, handler = self._timeout_handlers[0]
            if schedule <= now:
                self._timeout_handlers = self._timeout_handlers[1:]
                handler()
                sources_handled += 1
            if self._quit:
                return sources_handled
        if self._timeout_handlers and schedule:
            timeout = min(timeout, schedule - now)
        readable = []
        writable = []
        for handler in self._handlers:
            if not handler.fileno():
                continue
            if handler.readable():
                readable.append(handler)
            if handler.writable():
                writable.append(handler)
        if not readable and not writable:
            readable, writable, _unused = None, None, None
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

MainLoop = SelectMainLoop # pylint: disable-msg=C0103

if hasattr(select, "poll"):
    class PollMainLoop(MainLoopBase):
        """Main event loop based on the poll() syscall."""
        def __init__(self):
            MainLoopBase.__init__(self)
            self._quit = False
            self._handlers = {}
            self._volatile_handlers = {}
            self.poll = select.poll()
            self._timeout_handlers = []

        def add_io_handler(self, handler):
            """Add an I/O handler to the loop."""
            fileno = handler.fileno()
            if fileno is None:
                self._volatile_handlers[handler] = None
                return
            self._configure_io_handler(fileno, handler)

        def _configure_io_handler(self, fileno, handler):
            """Register an io-handler at the polling object."""
            if handler.volatile():
                self._volatile_handlers[handler] = fileno
            elif handler in self._volatile_handlers:
                del self._volatile_handlers[handler]
            self._handlers[fileno] = handler
            events = 0
            if handler.readable():
                events |= select.POLLIN
            if handler.writable():
                events |= select.POLLOUT
            if events:
                self.poll.register(fileno, events)

        def update_io_handler(self, handler):
            """Add an I/O handler to the loop."""
            fileno = handler.fileno()
            if handler in self._volatile_handlers:
                old_fileno = self._volatile_handlers[handler]
                if old_fileno and fileno != old_fileno:
                    try:
                        del self._handlers[old_fileno]
                    except KeyError:
                        pass
                    self.poll.unregister(old_fileno)
            elif fileno not in self._handlers:
                raise KeyError(handler)
            self._configure_io_handler(fileno, handler)

        def remove_io_handler(self, handler):
            """Remove an i/o-handler."""
            if handler in self._volatile_handlers:
                fileno = self._volatile_handlers[handler]
                del self._volatile_handlers[handler]
            else:
                fileno = handler.fileno()
            if fileno:
                del self._handlers[fileno]
                self.poll.unregister(fileno)
    
        def add_timeout_handler(self, timeout, handler):
            """Add a function to be called after `timeout` seconds."""
            self._timeout_handlers.append(timeout, handler)
            self._timeout_handlers.sort(key = lambda x: x[0])

        def loop_iteration(self, timeout = 60):
            """A loop iteration - check any scheduled events
            and I/O available and run the handlers.
            """
            sources_handled = 0
            now = time.time()
            schedule = None
            while self._timeout_handlers:
                schedule, handler = self._timeout_handlers[0]
                if schedule <= now:
                    self._timeout_handlers = self._timeout_handlers[1:]
                    handler()
                    sources_handled += 1
                if self._quit:
                    return sources_handled
            if self._timeout_handlers and schedule:
                timeout = min(timeout, schedule - now)
            for handler in self._volatile_handlers:
                self.update_io_handler(handler)
            events = self.poll.poll(timeout)
            for (fileno, event) in events:
                if event & select.POLLERR:
                    self._handlers[fileno].handle_err()
                if event & select.POLLHUP:
                    self._handlers[fileno].handle_hup()
                if event & select.POLLNVAL:
                    self._handlers[fileno].handle_nval()
                if event & select.POLLIN:
                    self._handlers[fileno].handle_read()
                if event & select.POLLOUT:
                    self._handlers[fileno].handle_write()
                sources_handled += 1
                self._configure_io_handler(fileno, self._handlers[fileno])
            return sources_handled
    MainLoop = PollMainLoop # pylint: disable-msg=C0103

class ReadingThread(threading.Thread):
    """A thread reading from io_handler.
    
    It can be used (together with `WrittingThread`) instead of 
    a main loop."""
    def __init__(self, io_handler, name = None):
        if name is None:
            name = u"{0!r} reader".format(io_handler)
        self.io_handler = io_handler
        threading.Thread.__init__(name = name)

    def run(self):
        """The thread function."""
        self.io_handler.set_blocking(True)
        while True:
            if self.io_handler.readable():
                self.io_handler.handle_read()
            elif not self.io_handler.wait_for_readability():
                break

class WrittingThread(threading.Thread):
    """A thread reading from io_handler.
    
    It can be used (together with `WrittingThread`) instead of 
    a main loop."""
    def __init__(self, io_handler, name = None):
        if name is None:
            name = u"{0!r} writer".format(io_handler)
        self.io_handler = io_handler
        threading.Thread.__init__(name = name)

    def run(self):
        """The thread function."""
        self.io_handler.set_blocking(True)
        while True:
            if self.io_handler.writable():
                self.io_handler.handle_write()
            elif not self.io_handler.wait_for_writability():
                break

