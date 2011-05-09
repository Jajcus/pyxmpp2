#
# (C) Copyright 2003-2010 Jacek Konieczny <jajcus@jajcus.net>
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
# pylint: disable-msg=W0611

"""Convenience module containing most important objects from pyxmpp package.

Suggested usage::
import pyxmpp.all

(imports all important names into pyxmpp namespace)"""

"""PyXMPP - Jabber/XMPP protocol implementation"""

from __future__ import absolute_import

__docformat__="restructuredtext en"

import pyxmpp2

from .stream import Stream
from .streambase import StreamError,FatalStreamError,StreamParseError
from .streamtls import StreamEncryptionRequired,tls_available,TLSSettings
from .clientstream import ClientStream,ClientStreamError
from .client import Client,ClientError
from .iq import Iq
from .presence import Presence
from .message import Message
from .jid import JID,JIDError
from .roster import Roster,RosterItem
from .exceptions import *

for name in dir():
    if not name.startswith("_") and name != "pyxmpp":
        setattr(pyxmpp,name,globals()[name])

# vi: sts=4 et sw=4
