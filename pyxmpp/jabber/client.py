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
"""Basic Jabber client functionality implementation.

Extends `pyxmpp.client` interface with legacy authentication
and basic Service Discovery handling.

Normative reference:
  - `JEP 78 <http://www.jabber.org/jeps/jep-0078.html>`__
  - `JEP 30 <http://www.jabber.org/jeps/jep-0030.html>`__
"""

__revision__="$Id: client.py,v 1.12 2004/10/07 22:28:11 jajcus Exp $"
__docformat__="restructuredtext en"

import logging

from pyxmpp.jabber.clientstream import LegacyClientStream
from pyxmpp.jabber.disco import DISCO_ITEMS_NS,DISCO_INFO_NS,DiscoInfo,DiscoItems,DiscoIdentity
from pyxmpp.client import Client
from pyxmpp.stanza import Stanza

class JabberClient(Client):
    def __init__(self,jid=None,password=None,server=None,port=5222,
            auth_methods=["sasl:DIGEST-MD5","digest"],
            tls_settings=None,keepalive=0):

        Client.__init__(self,jid,password,server,port,auth_methods,tls_settings,keepalive)
        self.stream_class=LegacyClientStream
        self.disco_items=None
        self.disco_info=None
        self.__logger=logging.getLogger("pyxmpp.jabber.JabberClient")

# public methods

    def connect(self,register=0):
        Client.connect(self)
        self.disco_items=DiscoItems()
        self.disco_info=DiscoInfo()
        self.disco_identity=DiscoIdentity(self.disco_info,
                            "pyxmpp based Jabber client",
                            "client","pc")

# private methods
    def __disco_info(self,iq):
        q=iq.get_query()
        if q.hasProp("node"):
            node=from_utf8(q.prop("node"))
        else:
            node=None
        info=self.disco_get_info(node,iq)
        if isinstance(info,DiscoInfo):
            resp=iq.make_result_response()
            self.__logger.debug("Disco-info query: %s preparing response: %s with reply: %s"
                % (iq.serialize(),resp.serialize(),info.xmlnode.serialize()))
            resp.set_content(info.xmlnode.copyNode(1))
        elif isinstance(info,stanza):
            resp=info
        else:
            resp=iq.make_error_response("item-not-found")
        self.__logger.debug("Disco-info response: %s" % (resp.serialize(),))
        self.stream.send(resp)

    def __disco_items(self,iq):
        q=iq.get_query()
        if q.hasProp("node"):
            node=from_utf8(q.prop("node"))
        else:
            node=None
        items=self.disco_get_items(node,iq)
        if isinstance(items,DiscoItems):
            resp=iq.make_result_response()
            self.__logger.debug("Disco-items query: %s preparing response: %s with reply: %s"
                % (iq.serialize(),resp.serialize(),items.xmlnode.serialize()))
            resp.set_content(items.xmlnode.copyNode(1))
        elif isinstance(items,Stanza):
            resp=items
        else:
            resp=iq.make_error_response("item-not-found")
        self.__logger.debug("Disco-items response: %s" % (resp.serialize(),))
        self.stream.send(resp)

# methods to override

    def authorized(self):
        Client.authorized(self)
        self.stream.set_iq_get_handler("query",DISCO_ITEMS_NS,self.__disco_items)
        self.stream.set_iq_get_handler("query",DISCO_INFO_NS,self.__disco_info)

    def disco_get_info(self,node,iq):
        to=iq.get_to()
        if to and to!=self.jid:
            return iq.make_error_response("recipient-unavailable")
        if not node and self.disco_info:
            return self.disco_info
        return None

    def disco_get_items(self,node,iq):
        to=iq.get_to()
        if to and to!=self.jid:
            return iq.make_error_response("recipient-unavailable")
        if not node and self.disco_items:
            return self.disco_items
        return None

# vi: sts=4 et sw=4
