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

from stream import Stream,StreamError,FatalStreamError,StreamParseError,tls_available,TLSSettings
from clientstream import ClientStream,ClientStreamError
from client import Client,ClientError
from iq import Iq
from presence import Presence
from message import Message
from jid import JID,JIDError
from stanza import StanzaError
from disco import DiscoInfo,DiscoItems,DiscoItem,DiscoIdentity
