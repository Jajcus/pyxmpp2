#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Example of the 'simple API' usage.

The simplest possible way to send an XMPP message.
"""

from getpass import getpass
from pyxmpp2.simple import send_message

your_jid = raw_input("Your jid: ")
your_password = getpass("Your password: ")
target_jid = raw_input("Target jid: ")
message = raw_input("Message: ")
    
send_message(your_jid, your_password, target_jid, message)
