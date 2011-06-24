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
    # pylint: disable-msg=R0903,R0921,R0922
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
    """Base class for PyXMPP2 events.
    """
    # pylint: disable-msg=W0232,R0903,R0921,R0922
    __metaclass__ = ABCMeta
    def __unicode__(self):
        raise NotImplementedError

QUIT = None
class QuitEvent(Event):
    """The `QUIT` event class."""
    # pylint: disable-msg=W0232,R0903
    def __unicode__(self):
        return "Quit"
QUIT = QuitEvent()
del QuitEvent

class EventHandler:
    """Base class for PyXMPP event handlers."""
    # pylint: disable-msg=W0232,R0903
    __metaclass__ = ABCMeta

def event_handler(event_class = None):
    """Method decorator generator for decorating event handlers.

    To be used on `EventHandler` subclass methods only.
    
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

class TimeoutHandler:
    """Base class for PyXMPP timeout handlers."""
    # pylint: disable-msg=W0232,R0903
    __metaclass__ = ABCMeta

def timeout_handler(interval, recurring = None):
    """Method decorator generator for decorating event handlers.
    
    To be used on `TimeoutHandler` subclass methods only.
    
    :Parameters:
        - `interval`: interval (in seconds) before the method will be called.
        - `recurring`: When `True`, the handler will be called each `interval`
          seconds, when `False` it will be called only once. If `True`,
          then the handler should return the next interval or `None` if it
          should not be called again.
    :Types:
        - `interval`: `float`
        - `recurring`: `bool`
    """
    def decorator(func):
        """The decorator"""
        func._pyxmpp_timeout = interval
        func._pyxmpp_recurring = recurring
        return func
    return decorator

class MainLoop:
    """Base class for main loop implementations."""
    # pylint: disable-msg=W0232
    __metaclass__ = ABCMeta
    def add_handler(self, handler):
        """Add a new handler to the main loop.

        :Parameters:
            `handler`: the handler object to add
        :Types:
            `handler`: `IOHandler` or `EventHandler` or `TimeoutHandler`
        """
        raise NotImplementedError
    def remove_handler(self, handler):
        """Add a new handler to the main loop.

        Do nothing if the handler is not registered at the main loop.

        :Parameters:
            `handler`: the handler object to add
        :Types:
            `handler`: `IOHandler` or `EventHandler` or `TimeoutHandler`
        """
        raise NotImplementedError
    def quit(self):
        """Make the loop stop after the current iteration."""
        raise NotImplementedError
    @property
    def started(self):
        """`True` then the loop has been started.
        """
        raise NotImplementedError
    @property
    def finished(self):
        """`True` then the loop has been finished or is about to finish (the
        final iteration in progress).
        """
        raise NotImplementedError
    def loop(self, timeout = 1):
        """Run the loop.
        
        :Parameters:
            - `timeout`: default polling interval in seconds
        :Types:
            - `timeout`: `float`
        """
        raise NotImplementedError
    def loop_iteration(self, timeout = 1):
        """Single loop iteration."""
        raise NotImplementedError
