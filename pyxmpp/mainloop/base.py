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

"""Main loop implementation Base.
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import time
import logging

from .events import EventDispatcher
from .interfaces import EventHandler, IOHandler, MainLoop, QUIT
from ..settings import XMPPSettings

logger = logging.getLogger("pyxmpp.mainloop.base")

class MainLoopBase(MainLoop):
    """Base class for main loop implementations."""
    # pylint: disable-msg=W0223
    def __init__(self, settings = None, handlers = None):
        if settings is None:
            self.settings = XMPPSettings()
        else:
            self.settings = settings
        if not handlers:
            handlers = []
        self.event_dispatcher = EventDispatcher(self.settings, handlers)
        self.event_queue = self.settings["event_queue"]
        self._quit = False
        self._started = False
        for handler in handlers:
            if isinstance(handler, IOHandler):
                self.add_io_handler(handler)
            elif isinstance(handler, EventHandler):
                self.event_dispatcher.add_handler(handler)
    def finished(self):
        return self._quit
    def started(self):
        return self._started
    def quit(self):
        """Make the loop stop after the current iteration."""
        self.event_queue.put(QUIT)
    def loop(self, timeout = 1):
        while not self._quit:
            self.loop_iteration(timeout)
    def loop_iteration(self, timeout):
        if self.check_events():
            return
        time.sleep(timeout)
    def check_events(self):
        if self.event_dispatcher.flush() is QUIT:
            self._quit = True
            return True
        return False

