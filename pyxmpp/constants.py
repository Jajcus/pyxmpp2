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

"Common XMPP constants."""

XML_NS = "http://www.w3.org/XML/1998/namespace"

STREAM_NS = "http://etherx.jabber.org/streams"

STANZA_CLIENT_NS = "jabber:client"
STANZA_SERVER_NS = "jabber:server"

STANZA_NAMESPACES = (STANZA_CLIENT_NS, STANZA_SERVER_NS)

STANZA_ERROR_NS='urn:ietf:params:xml:ns:xmpp-stanzas'
STREAM_ERROR_NS='urn:ietf:params:xml:ns:xmpp-streams'
PYXMPP_ERROR_NS='http://pyxmpp.jajcus.net/xmlns/errors'

# build the _QNP (QName prefix) constants
for name, value in globals().items():
    if name.endswith("_NS"):
        globals()[name[:-3] + "_QNP"] = "{{{0}}}".format(value)

XML_LANG_QNAME = XML_QNP + "lang"
