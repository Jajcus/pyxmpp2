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

from clientstream import LegacyClientStream
from disco import DiscoInfo,DiscoItems,DiscoItem,DiscoIdentity
from pyxmpp.client import Client,ClientError,FatalClientError

class JabberClient(Client):
	def __init__(self,jid=None,password=None,server=None,port=5222,
			auth_methods=["sasl:DIGEST-MD5","digest"],
			tls_settings=None,keepalive=0):

		Client.__init__(self,jid,password,server,port,auth_methods,tls_settings,keepalive)
		self.stream_class=LegacyClientStream
		self.disco_items=None
		self.disco_info=None

# public methods

	def connect(self,register=0):
		Client.connect(self)
		self.disco_items=DiscoItems()
		self.disco_info=DiscoInfo()
		self.disco_info.add_feature("iq")
		self.disco_identity=DiscoIdentity(self.disco_info,
							"pyxmpp based Jabber client",
							"client","pc")

# private methods
	def __disco_info(self,iq):
		resp=iq.make_result_response()
		self.debug("Disco-info query: %s preparing response: %s with reply: %s" 
			% (iq.serialize(),resp.serialize(),self.disco_info.xmlnode.serialize()))
		resp.set_content(self.disco_info.xmlnode.copyNode(1))
		self.debug("Disco-info response: %s" % (resp.serialize(),))
		self.stream.send(resp)

	def __disco_items(self,iq):
		resp=iq.make_result_response()
		self.debug("Disco-items query: %s preparing response: %s with reply: %s" 
			% (iq.serialize(),resp.serialize(),self.disco_info.xmlnode.serialize()))
		resp.set_content(self.disco_items.xmlnode.copyNode(1))
		self.debug("Disco-items response: %s" % (resp.serialize(),))
		self.stream.send(resp)

	def authorized(self):
		Client.authorized(self)
		self.stream.set_iq_get_handler("query","http://jabber.org/protocol/disco#items",
									self.__disco_items)
		self.stream.set_iq_get_handler("query","http://jabber.org/protocol/disco#info",
									self.__disco_info)
