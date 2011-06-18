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

import logging

from .events import EventQueue, QUIT
from .abc import EventHandler, IOHandler, MainLoop

logger = logging.getLogger("pyxmpp.mainloop.base")

class MainLoopBase(MainLoop):
    """Base class for main loop implementations."""
    # pylint: disable-msg=W0223
    def __init__(self, handlers = None):
        if not handlers:
            handlers = []
        self.event_queue = EventQueue(handlers)
        self._quit = False
        event_handlers = []
        for handler in handlers:
            if isinstance(handler, IOHandler):
                self.add_io_handler(handler)
            elif isinstance(handler, EventHandler):
                event_handlers.append(handler)
    def quit(self):
        """Make the loop stop after the current iteration."""
        self.event_queue.post_event(QUIT)
