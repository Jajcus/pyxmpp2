#
# (C) Copyright 2003 Jacek Konieczny <jajcus@bnet.pl>
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

"""PyXMPP - Jabber/XMPP protocol implementation"""

__revision__="$Id: __init__.py,v 1.15 2004/09/20 21:07:19 jajcus Exp $"
__docformat__="restructuredtext en"

from pyxmpp.stream import Stream,StreamError,FatalStreamError,StreamParseError
from pyxmpp.stream import StreamEncryptionRequired,tls_available,TLSSettings
from pyxmpp.clientstream import ClientStream,ClientStreamError
from pyxmpp.client import Client,ClientError
from pyxmpp.iq import Iq
from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.jid import JID,JIDError
from pyxmpp.stanza import StanzaError
from pyxmpp.roster import Roster,RosterItem

# vi: sts=4 et sw=4
