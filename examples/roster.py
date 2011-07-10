#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
A roster interface example.

Usage:

    roster.py JID show [--presence]

    roster.py JID monitor [--presence]

    roster.py JID add [--subscribe] [--approve] CONTACT [NAME] [GROUP ...]

    roster.py JID remove CONTACT

    roster.py JID update CONTACT [NAME] [GROUP [GROUP ...]]

        positional arguments:
            CONTACT     The JID to add
            NAME        Contact name
            GROUP       Group names

    roster.py --help 

        for the general help
"""

import os
import sys
import logging
from getpass import getpass
import argparse

from collections import defaultdict

from pyxmpp2.jid import JID
from pyxmpp2.presence import Presence
from pyxmpp2.client import Client
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.interfaces import XMPPFeatureHandler, presence_stanza_handler
from pyxmpp2.streamevents import AuthorizedEvent, DisconnectedEvent
from pyxmpp2.roster import RosterReceivedEvent, RosterUpdatedEvent

class RosterTool(EventHandler, XMPPFeatureHandler):
    """Echo Bot implementation."""
    def __init__(self, my_jid, args, settings):
        self.args = args
        self.client = Client(my_jid, [self], settings)
        self.presence = defaultdict(dict)

    def run(self):
        """Request client connection and start the main loop."""
        if self.args.roster_cache and os.path.exists(self.args.roster_cache):
            logging.info(u"Loading roster from {0!r}"
                                            .format(self.args.roster_cache))
            try:
                self.client.roster_client.load_roster(self.args.roster_cache)
            except (IOError, ValueError), err:
                logging.error(u"Could not load the roster: {0!r}".format(err))
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
        if not self.args.presence:
            return
        presences = self.presence.get(item.jid)
        if not presences:
            print u"    OFFLINE"
        else:
            print u"    ONLINE:"
            for jid, presence in presences.items():
                if presence.show:
                    show = u": [{0}]".format(presence.show)
                elif not presence.status:
                    show = u""
                else:
                    show = u":"
                if presence.status:
                    status = u" '{0}'".format(presence.status)
                else:
                    status = u""
                print u"      /{0}{1}{2}".format(jid.resource, show, status)

    @event_handler(RosterReceivedEvent)
    def handle_roster_received(self, event):
        if self.args.action == "show":
            if self.args.presence:
                logging.info(u"Waiting for incoming presence information...")
                self.client.main_loop.delayed_call(5, self.delayed_show)
            else:
                self.print_roster()
                self.client.disconnect()
        elif self.args.action == "monitor":
            self.print_roster()
        elif self.args.action == "add":
            self.add_contact()
        elif self.args.action == "remove":
            self.remove_contact()
        elif self.args.action == "update":
            self.update_contact()
        else:
            self.client.disconnect()

    def delayed_show(self):
        self.print_roster()
        self.client.disconnect()

    def print_roster(self):
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

    def add_contact(self):
        roster_client = self.client.roster_client
        roster_client.add_item(jid = JID(self.args.contact),
                name = self.args.name, groups = self.args.groups,
                                        callback = self._add_success,
                                            error_callback = self._add_error)
        if self.args.subscribe:
            presence = Presence(to_jid = self.args.contact,
                                            stanza_type = 'subscribe')
            self.client.send(presence)
        if self.args.approve:
            if "pre-approvals" not in roster_client.server_features:
                logging.error("Subscription pre-approvals not available")
            else:
                presence = Presence(to_jid = self.args.contact,
                                                stanza_type = 'subscribed')
                self.client.send(presence)

    def _add_success(self, item):
        print "Roster item added: {0}".format(item.jid)
        self.client.disconnect()

    def _add_error(self, stanza):
        if stanza:
            error = stanza.error
            if error.text:
                print "Roster item add failed: {0}".format(
                                                        error.condition_name)
            else:
                print "Roster item add failed: {0} ({1})".format(
                                            error.condition_name, error.text)
        else:
            print "Roster item add failed: timeout"
        self.client.disconnect()

    def update_contact(self):
        roster_client = self.client.roster_client
        roster_client.update_item(jid = JID(self.args.contact),
                name = self.args.name, groups = self.args.groups,
                                        callback = self._update_success,
                                            error_callback = self._update_error)

    def _update_success(self, item):
        print "Roster item updateed: {0}".format(item.jid)
        self.client.disconnect()

    def _update_error(self, stanza):
        if stanza:
            error = stanza.error
            if error.text:
                print "Roster item update failed: {0}".format(
                                                        error.condition_name)
            else:
                print "Roster item update failed: {0} ({1})".format(
                                            error.condition_name, error.text)
        else:
            print "Roster item update failed: timeout"
        self.client.disconnect()

    def remove_contact(self):
        roster_client = self.client.roster_client
        roster_client.remove_item(jid = JID(self.args.contact),
                                        callback = self._rm_success,
                                            error_callback = self._rm_error)

    def _rm_success(self, item):
        print "Roster item removed: {0}".format(item.jid)
        self.client.disconnect()

    def _rm_error(self, stanza):
        if stanza:
            error = stanza.error
            if error.text:
                print "Roster item remove failed: {0}".format(
                                                        error.condition_name)
            else:
                print "Roster item remove failed: {0} ({1})".format(
                                            error.condition_name, error.text)
        else:
            print "Roster item remove failed: timeout"
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
        print
    
    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
        if self.client.roster and self.args.roster_cache:
            logging.info(u"Saving roster to {0!r}"
                                            .format(self.args.roster_cache))
            self.client.roster_client.save_roster(self.args.roster_cache)
        return QUIT

    @event_handler()
    def handle_all(self, event):
        """Log all events."""
        logging.info(u"-- {0}".format(event))

    @presence_stanza_handler()
    def handle_available_presence(self, stanza):
        jid = stanza.from_jid
        self.presence[jid.bare()][jid] = stanza
        if self.args.action != "monitor":
            return
        if not self.args.presence:
            return
        print u"Presence change:"
        if stanza.show:
            show = u": [{0}]".format(stanza.show)
        elif not stanza.status:
            show = u""
        else:
            show = u":"
        if stanza.status:
            status = u" '{0}'".format(stanza.status)
        else:
            status = u""
        print u"  {0} is now ONLINE{1}{2}".format(jid, show, status)
        print
    
    @presence_stanza_handler("unavailable")
    def handle_unavailable_presence(self, stanza):
        jid = stanza.from_jid
        self.presence[jid.bare()].pop(jid, None)

        if self.args.action != "monitor":
            return
        if not self.args.presence:
            return
        print u"Presence change:"
        if stanza.status:
            status = u": '{0}'".format(stanza.status)
        else:
            status = u""
        print u"  {0} is now OFFLINE{1}".format(jid, status)
        print
 
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
    parser.add_argument('--roster-cache', 
                        help = 'Store roster in this file')
    parser.add_argument('jid', metavar = 'JID', 
                                        help = 'The bot JID')
    subparsers = parser.add_subparsers(help = 'Action', dest = "action")
    show_p = subparsers.add_parser('show', help = 'Show roster and exit')
    show_p.add_argument('--presence', action = 'store_true',
                        help = 'Wait 5 s for contact presence information'
                                ' and display it with the roster')
    mon_p = subparsers.add_parser('monitor', help = 
                                        'Show roster and subsequent changes')
    mon_p.add_argument('--presence', action = 'store_true',
                        help = 'Show contact presence changes too')
    add_p = subparsers.add_parser('add', help = 'Add an item to the roster')
    add_p.add_argument('--subscribe', action = 'store_true', dest = 'subscribe',
                        help = 'Request a presence subscription too')
    add_p.add_argument('--approve', action = 'store_true', dest = 'approve',
                        help = 'Pre-approve subscription from the contact'
                                                ' (requires server support)')
    add_p.add_argument('contact', metavar = 'CONTACT', help = 'The JID to add')
    add_p.add_argument('name', metavar = 'NAME', nargs = '?',
                                            help = 'Contact name')
    add_p.add_argument('groups', metavar = 'GROUP', nargs = '*',
                                            help = 'Group names')
    rm_p = subparsers.add_parser('remove',
                                    help = 'Remove an item from the roster')
    rm_p.add_argument('contact', metavar = 'CONTACT',
                                    help = 'The JID to remove')
    upd_p = subparsers.add_parser('update', 
                                    help = 'Update an item in the roster')
    upd_p.add_argument('contact', metavar = 'CONTACT',
                                    help = 'The JID to update')
    upd_p.add_argument('name', metavar = 'NAME', nargs = '?',
                                            help = 'Contact name')
    upd_p.add_argument('groups', metavar = 'GROUP', nargs = '*',
                                            help = 'Group names')

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
        if getattr(args, "contact", None):
            args.contact = args.contact.decode("utf-8")
        if getattr(args, "name", None):
            args.name = args.name.decode("utf-8")
        if getattr(args, "groups", None):
            args.groups = [g.decode("utf-8") for g in args.groups]

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
           
    if args.action == "monitor" or args.action == "show" and args.presence:
        # According to RFC6121 it could be None for 'monitor' (no need to send
        # initial presence to request roster), but Google seems to require that
        # to send roster pushes
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
