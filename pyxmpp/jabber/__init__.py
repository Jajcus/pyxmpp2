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

"""JSF defined XMPP extension and legacy Jabber protocol elements"""

from clientstream import LegacyClientStream
from client import JabberClient as Client
from disco import DISCO_NS,DISCO_INFO_NS,DISCO_ITEMS_NS
from disco import DiscoInfo,DiscoItems,DiscoItem,DiscoIdentity
from vcard import VCARD_NS,VCard
