#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Example of using the pyxmpp2.ext.version module to request version information
from the remote entity.
"""

import sys
import logging
from getpass import getpass
import argparse

from pyxmpp2.jid import JID
from pyxmpp2.ext.version import request_software_version
from pyxmpp2.client import Client
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.streamevents import AuthorizedEvent, DisconnectedEvent

class VersionChecker(EventHandler):
    """Version checker implementation."""
    def __init__(self, my_jid, target_jid, settings):
        self.client = Client(my_jid, [self], settings)
        self.target_jid = target_jid

    def run(self):
        """Request client connection and start the main loop."""
        self.client.connect()
        self.client.run()

    def disconnect(self):
        """Request disconnection and let the main loop run for a 2 more
        seconds for graceful disconnection."""
        self.client.disconnect()
        self.client.run(timeout = 2)

    @event_handler(AuthorizedEvent)
    def handle_authorized(self, event):
        """Send the initial presence after log-in."""
        request_software_version(self.client, self.target_jid,
                                        self.success, self.failure)

    def success(self, version):
        print("Name: {0}".format(version.name))
        print("Version: {0}".format(version.version))
        if version.os_name is not None:
            print("Operating System: {0}".format(version.os_name))
        else:
            print("Operating System name not available")
        self.client.disconnect()

    def failure(self, stanza):
        print("Version query failed")
        if stanza and stanza.stanza_type == "error":
            cond_name = stanza.error.condition_name
            text = stanza.error.text
            if text:
                print("Error: {0} ({1})".format(cond_name, text))
            else:
                print("Error: {0}".format(cond_name))
        self.client.disconnect()

    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
        """Quit the main loop upon disconnection."""
        return QUIT
    
def main():
    """Parse the command-line arguments and run the tool."""
    parser = argparse.ArgumentParser(description = 'XMPP version checker',
                                    parents = [XMPPSettings.get_arg_parser()])
    parser.add_argument('source', metavar = 'SOURCE', 
                                        help = 'Source JID')
    parser.add_argument('target', metavar = 'TARGET', nargs = '?',
                            help = 'Target JID (default: domain of SOURCE)')
    parser.add_argument('--debug',
                        action = 'store_const', dest = 'log_level',
                        const = logging.DEBUG, default = logging.INFO,
                        help = 'Print debug messages')
    parser.add_argument('--quiet', const = logging.ERROR,
                        action = 'store_const', dest = 'log_level',
                        help = 'Print only error messages')
    args = parser.parse_args()
    settings = XMPPSettings()
    settings.load_arguments(args)
    
    if settings.get("password") is None:
        password = getpass("{0!r} password: ".format(args.source))
        if sys.version_info.major < 3:
            password = password.decode("utf-8")
        settings["password"] = password

    if sys.version_info.major < 3:
        args.source = args.source.decode("utf-8")

    source = JID(args.source)

    if args.target:
        if sys.version_info.major < 3:
            args.target = args.target.decode("utf-8")
        target = JID(args.target)
    else:
        target = JID(source.domain)

    logging.basicConfig(level = args.log_level)

    checker = VersionChecker(source, target, settings)
    try:
        checker.run()
    except KeyboardInterrupt:
        checker.disconnect()

if __name__ == '__main__':
    main()
