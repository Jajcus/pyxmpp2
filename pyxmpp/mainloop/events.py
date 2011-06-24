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
# pylint: disable-msg=W0201

"""PyXMPP events."""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import Queue
import threading
import logging
import inspect

from collections import defaultdict

logger = logging.getLogger("pyxmpp.mainloop.events")

from .interfaces import EventHandler, QUIT
from ..settings import XMPPSettings

class EventDispatcher(object):
    """Dispatches events from an event queue to event handlers.

    Events are `.interfaces.Event` instances stored in the event queue
    (defined by the "event_queue" setting). Event handlers are `EventHandler`
    subclass instance methods decorated with the `event_handler` decorator.

    :Ivariables:
        - `queue`: the event queue
        - `handlers`: list of handler objects
        - `lock`: the thread synchronisation lock
        - `_handlers_map`: mapping of event type to list of handler methods
    :Types:
        - `queue`: `Queue.Queue`
        - `handlers`: `list` of `EventHandler`
        - `lock`: `threading.RLock`
        - `_handlers_map`: `type` -> `list` of callable mapping
    """
    def __init__(self, settings = None, handlers = None):
        """Initialize the event dispatcher.

        :Parameters:
            - `settings`: the settings. "event_queue" settings provides
            the event queue object.
            - `handlers`: the initial list of event handler objects.
        :Types:
            - `settings`: `XMPPSettings`
            - `handlers`: iterable of objects
        """
        if settings is None:
            settings = XMPPSettings()
        self.queue = settings["event_queue"]
        self._handlers_map = defaultdict(list)
        if handlers:
            self.handlers = list(handlers)
        else:
            self.handlers = []
        self._update_handlers()
        self.lock = threading.RLock()

    def add_handler(self, handler):
        """Add a handler object.

        :Parameters:
            `handler`: the object providing event handler methods
        :Types:
            `handler`: `EventHandler`
        """
        if not isinstance(handler, EventHandler):
            raise TypeError, "Not an EventHandler"
        with self.lock:
            if handler in self.handlers:
                return
            self.handlers.append(handler)
            self._update_handlers()

    def remove_handler(self, handler):
        """Remove a handler object.
        
        :Parameters:
            `handler`: the object to remove
        """
        with self.lock:
            if handler in self.handlers:
                self.handlers.remove(handler)
                self._update_handlers()

    def _update_handlers(self):
        """Update `self.handler_map` after `self.handlers` have been
        modified."""
        handler_map = defaultdict(list)
        for i, obj in enumerate(self.handlers):
            for dummy, handler in inspect.getmembers(obj, callable):
                if not hasattr(handler, "_pyxmpp_event_handled"):
                    continue
                # pylint: disable-msg=W0212
                event_class = handler._pyxmpp_event_handled
                handler_map[event_class].append( (i, handler) )
        self._handler_map = handler_map

    def dispatch(self, block = False, timeout = None):
        """Get the next event from the queue and pass it to
        the appropriate handlers.

        :Parameters:
            `block`: wait for event if the queue is empty
            `timeout`: maximum time, in seconds, to wait if `block` is `True`
        :Types:
            `block`: `bool`
            `timeout`: `float`

        :Return: the event handled (may be `QUIT`) or `None`
        """
        logger.debug(" dispatching...")
        try:
            event = self.queue.get(block, timeout)
        except Queue.Empty:
            logger.debug("    queue empty")
            return None
        try:
            logger.debug("    event: {0!r}".format(event))
            if event is QUIT:
                return QUIT
            handlers = list(self._handler_map[None])
            klass = event.__class__
            if klass in self._handler_map:
                handlers += self._handler_map[klass]
            logger.debug("    handlers: {0!r}".format(handlers))
            handlers.sort() # to restore the original order of handler objects
            for dummy, handler in handlers:
                logger.debug(u"  passing the event to: {0!r}".format(handler))
                if handler(event) and event is not QUIT:
                    return event
            return event
        finally:
            self.queue.task_done()

    def flush(self, dispatch = True):
        """Read all events currently in the queue and dispatch them to the
        handlers unless `dispatch` is `False`.

        Note: If the queue contains `QUIT` the events after it won't be
        removed.

        :Parameters:
            `dispatch`: if the events should be handled (`True`) or ignored
            (`False`)

        :Return: `QUIT` if the `QUIT` event was reached.
        """
        if dispatch:
            while True:
                event = self.dispatch(False)
                if event in (None, QUIT):
                    return event
        else:
            while True:
                try:
                    self.queue.get(False)
                except Queue.Empty:
                    return None

    def loop(self):
        """Wait for and dispatch events until `QUIT` is reached.
        """
        while self.dispatch(True) is not QUIT:
            pass

XMPPSettings.add_defaults({
                            u"event_queue_max_size": None, 
                            })

def event_queue_factory(settings):
    """Create the default event queue object.
    
    Use the "event_queue_max_size" setting for the maximum queue size.
    """
    return Queue.Queue(settings["event_queue_max_size"])

XMPPSettings.add_default_factory("event_queue", event_queue_factory, True)

