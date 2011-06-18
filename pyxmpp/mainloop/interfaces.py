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

"""Abstract base classes for the main loop framework.
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

from abc import ABCMeta

class IOHandlerPrepareResult(object):
    """Result of the `IOHandler.prepare` method."""
    # pylint: disable-msg=R0903
    pass

class HandlerReady(IOHandlerPrepareResult):
    """Returned by the `IOHandler.prepare` method
    when the object is ready to handle I/O events and doesn't need further
    calls to the `IOHandler.prepare` method.
    """
    # pylint: disable-msg=R0903
    def __repr__(self):
        return "HandlerReady()"

class PrepareAgain(IOHandlerPrepareResult):
    """Returned by the `IOHandler.prepare` method
    when the method needs to be called again.

    :Ivariables:
      - `timeout`: how long may the main loop wait before calling
        `IOHandler.prepare` again. `None` means wait until the next loop
        iteration whenever it happens, `0` - do not wait on I/O in this
        iteration.
    """
    # pylint: disable-msg=R0903
    def __init__(self, timeout = None):
        IOHandlerPrepareResult.__init__(self)
        self.timeout = timeout
    def __repr__(self):
        if self.timeout is None:
            return "PrepareAgain({0!r})".format(self.timeout)
        else:
            return "PrepareAgain()"

class IOHandler:
    """Wrapper for a socket or a file descriptor to be used in event loop
    or for I/O threads."""
    # pylint: disable-msg=W0232,R0921
    __metaclass__ = ABCMeta
    def fileno(self):
        """Return file descriptor to poll or select."""
        raise NotImplementedError
    def set_event_queue(self, queue):
        """Set the event queue to be used by the IOHandler."""
        pass
    def set_blocking(self, blocking = True):
        """Force the handler into blocking or nonblocking mode, so the
        `handle_write()` and `handle_read()` methods are guaranteed to block
        for some time (or fail if not `is_readable()` or `is_writable()` if nothing
        can be written or there is nothing to read."""
        raise NotImplementedError
    def is_readable(self):
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
    def is_writable(self):
        """
        :Return: `True` when the I/O channel can be written to
        """
        raise NotImplementedError
    def prepare(self):
        """
        Prepare the I/O handler for the event loop or an event loop 
        iteration. 

        :Return: `HandlerReady()` if there is no need to call `prepare` again
        or `PrepareAgain()` otherwise.
        :Returntype: `IOHandlerPrepareResult`
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

class Event:
    __metaclass__ = ABCMeta
    def __unicode__(self):
        raise NotImplementedError

class EventHandler:
    """Base class for PyXMPP event handlers."""
    # pylint: disable-msg=W0232,R0903
    __metaclass__ = ABCMeta

def event_handler(event_class = None):
    """Method decorator generator for decorating event handlers.
    
    :Parameters:
        - `event_class`: event class expected
    :Types:
        - `event_class`: subclass of `Event`
    """
    def decorator(func):
        """The decorator"""
        func._pyxmpp_event_handled = event_class
        return func
    return decorator

class MainLoop:
    """Base class for main loop implementations."""
    __metaclass__ = ABCMeta
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
        raise NotImplementedError
    def started(self):
        raise NotImplementedError
    def finished(self):
        raise NotImplementedError
    def run(self, timeout = 60):
        """Run the loop."""
        raise NotImplementedError
    def loop_iteration(self, timeout = 60):
        """Single loop iteration."""
        raise NotImplementedError
