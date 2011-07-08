#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
An 'echo bot' – simple client that just confirms any presence subscriptions
and echoes incoming messages.
"""

import sys
import logging
from getpass import getpass
import argparse

from pyxmpp2.jid import JID
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence
from pyxmpp2.client import Client
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.streamevents import AuthorizedEvent, DisconnectedEvent
from pyxmpp2.interfaces import XMPPFeatureHandler
from pyxmpp2.interfaces import presence_stanza_handler, message_stanza_handler
from pyxmpp2.ext.version import VersionProvider

class EchoBot(EventHandler, XMPPFeatureHandler):
    """Echo Bot implementation."""
    def __init__(self, my_jid, settings):
        version_provider = VersionProvider(settings)
        self.client = Client(my_jid, [self, version_provider], settings)

    def run(self):
        """Request client connection and start the main loop."""
        self.client.connect()
        self.client.run()

    def disconnect(self):
        """Request disconnection and let the main loop run for a 2 more
        seconds for graceful disconnection."""
        self.client.disconnect()
        self.client.run(timeout = 2)

    @presence_stanza_handler("subscribe")
    def handle_presence_subscribe(self, stanza):
        logging.info(u"{0} requested presence subscription"
                                                    .format(stanza.from_jid))
        presence = Presence(to_jid = stanza.from_jid.bare(),
                                                    stanza_type = "subscribe")
        return [stanza.make_accept_response(), presence]

    @presence_stanza_handler("subscribed")
    def handle_presence_subscribed(self, stanza):
        logging.info(u"{0!r} accepted our subscription request"
                                                    .format(stanza.from_jid))
        return True

    @presence_stanza_handler("unsubscribe")
    def handle_presence_unsubscribe(self, stanza):
        logging.info(u"{0} canceled presence subscription"
                                                    .format(stanza.from_jid))
        presence = Presence(to_jid = stanza.from_jid.bare(),
                                                    stanza_type = "unsubscribe")
        return [stanza.make_accept_response(), presence]

    @presence_stanza_handler("unsubscribed")
    def handle_presence_unsubscribed(self, stanza):
        logging.info(u"{0!r} acknowledged our subscrption cancelation"
                                                    .format(stanza.from_jid))
        return True

    @message_stanza_handler()
    def handle_message(self, stanza):
        """Echo every non-error ``<message/>`` stanza.
        
        Add "Re: " to subject, if any.
        """
        if stanza.subject:
            subject = u"Re: " + stanza.subject
        else:
            subject = None
        msg = Message(stanza_type = stanza.stanza_type,
                        from_jid = stanza.to_jid, to_jid = stanza.from_jid,
                        subject = subject, body = stanza.body,
                        thread = stanza.thread)
        return msg

    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
        """Quit the main loop upon disconnection."""
        return QUIT
    
    @event_handler()
    def handle_all(self, event):
        """Log all events."""
        logging.info(u"-- {0}".format(event))

def main():
    """Parse the command-line arguments and run the bot."""
    parser = argparse.ArgumentParser(description = 'XMPP echo bot',
                                    parents = [XMPPSettings.get_arg_parser()])
    parser.add_argument('jid', metavar = 'JID', 
                                        help = 'The bot JID')
    parser.add_argument('--debug',
                        action = 'store_const', dest = 'log_level',
                        const = logging.DEBUG, default = logging.INFO,
                        help = 'Print debug messages')
    parser.add_argument('--quiet', const = logging.ERROR,
                        action = 'store_const', dest = 'log_level',
                        help = 'Print only error messages')
    parser.add_argument('--trace', action = 'store_true',
                        help = 'Print XML data sent and received')

    args = parser.parse_args()
    settings = XMPPSettings({
                            "software_name": "Echo Bot"
                            })
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

    bot = EchoBot(JID(args.jid), settings)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.disconnect()

if __name__ == '__main__':
    main()
