#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
A roster interface example.
"""

import sys
import logging
from getpass import getpass
import argparse

from pyxmpp2.jid import JID
from pyxmpp2.presence import Presence
from pyxmpp2.client import Client
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.streamevents import AuthorizedEvent, DisconnectedEvent
from pyxmpp2.roster import RosterReceivedEvent, RosterUpdatedEvent

class RosterTool(EventHandler):
    """Echo Bot implementation."""
    def __init__(self, my_jid, args, settings):
        self.args = args
        self.client = Client(my_jid, [self], settings)

    def run(self):
        """Request client connection and start the main loop."""
        self.client.connect()
        self.client.run()

    def disconnect(self):
        """Request disconnection and let the main loop run for a 2 more
        seconds for graceful disconnection.
        """
        self.client.disconnect()
        self.client.run(timeout = 2)

    def print_item(self, item):
        print u"    JID: {0}".format(item.jid)
        if item.name is not None:
            print u"    Name: {0}".format(item.name)
        print u"    Subscription: {0}".format(item.subscription)
        if item.ask:
            print u"    Pending {0}".format(item.ask)
        if item.approved:
            print u"    Approved"
        if item.groups:
            groups = u",".join(
                            [u"'{0}'".format(g) for g in item.groups])
            print u"    Groups: {0}".format(groups)

    @event_handler(RosterReceivedEvent)
    def handle_roster_received(self, event):
        if self.args.action not in ("show", "monitor"):
            return
        roster = self.client.roster  # event.roster would also do
        print "Roster received:"
        if roster.version is None:
            print u"  (not versioned)"
        else:
            print u"  Version: '{0}'".format(roster.version)
        if len(roster):
            print u"  Items:"
            for item in roster.values():
                self.print_item(item)
                print
        else:
            print "  Empty"
            print
        if self.args.action == "show":
            self.client.disconnect()

    @event_handler(RosterUpdatedEvent)
    def handle_roster_update(self, event):
        if self.args.action != "monitor":
            return
        item = event.item
        if item.subscription == "remove":
            print u"Item removed:"
            print u"  JID: {0}".format(item.jid)
        else:
            if event.old_item:
                print u"Item modified:"
            else:
                print u"Item added:"
            print u"  JID: {0}".format(item.jid)
            self.print_item(item)
    
    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
        return QUIT

    @event_handler()
    def handle_all(self, event):
        """Log all events."""
        logging.info(u"-- {0}".format(event))

def main():
    """Parse the command-line arguments and run the bot."""
    parser = argparse.ArgumentParser(description = 'XMPP echo bot',
                                    parents = [XMPPSettings.get_arg_parser()])
    parser.add_argument('--debug',
                        action = 'store_const', dest = 'log_level',
                        const = logging.DEBUG, default = logging.INFO,
                        help = 'Print debug messages')
    parser.add_argument('--quiet', const = logging.ERROR,
                        action = 'store_const', dest = 'log_level',
                        help = 'Print only error messages')
    parser.add_argument('--trace', action = 'store_true',
                        help = 'Print XML data sent and received')
    parser.add_argument('jid', metavar = 'JID', 
                                        help = 'The bot JID')
    subparsers = parser.add_subparsers(help = 'Action', dest = "action")
    subparsers.add_parser('show', help = 'Show roster and exit')
    subparsers.add_parser('monitor', help = 
                                        'Show roster and subsequent changes')
    args = parser.parse_args()
    settings = XMPPSettings()
    settings.load_arguments(args)

    if settings.get("password") is None:
        password = getpass("{0!r} password: ".format(args.jid))
        if sys.version_info.major < 3:
            password = password.decode("utf-8")
        settings["password"] = password

    if sys.version_info.major < 3:
        args.jid = args.jid.decode("utf-8")

    logging.basicConfig(level = args.log_level)
    if args.trace:
        print "enabling trace"
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        for logger in ("pyxmpp2.IN", "pyxmpp2.OUT"):
            logger = logging.getLogger(logger)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.propagate = False
           
    if args.action == "monitor":        
        # According to RFC6121 it could be None (no need to send initial
        # presence to request roster), but Google seems to require
        # that to send roster pushes
        settings["initial_presence"] = Presence(priority = -1)
    else:
        settings["initial_presence"] = None

    tool = RosterTool(JID(args.jid), args, settings)
    try:
        tool.run()
    except KeyboardInterrupt:
        tool.disconnect()

if __name__ == '__main__':
    main()
