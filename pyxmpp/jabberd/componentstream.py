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

import libxml2
import sha
import time
from types import UnicodeType

from pyxmpp.stream import Stream,StreamError,FatalStreamError,SASLNotAvailable,SASLMechanismNotAvailable
from pyxmpp.stream import StreamAuthenticationError,StanzaFactory
from pyxmpp.iq import Iq
from pyxmpp.stanza import common_doc
from pyxmpp.jid import JID
from pyxmpp.utils import to_utf8,from_utf8

class ComponentStreamError(StreamError):
	pass

class FatalComponentStreamError(FatalStreamError):
	pass

class LegacyAuthenticationError(StreamAuthenticationError):
	pass

class ComponentStream(Stream):
	def __init__(self,jid,secret,server,port,keepalive=0):
		Stream.__init__(self,"jabber:component:accept",
					sasl_mechanisms=[],
					tls_settings=None,
					keepalive=keepalive)
		self.server=server
		self.port=port
		self.jid=jid
		self.secret=secret
		self.process_all_stanzas=1
	
	def _reset(self):
		Stream._reset(self)

	def connect(self,server=None,port=None):
		self.lock.acquire()
		try:
			self._connect(server,port)
		finally:
			self.lock.release()
		
	def _connect(self,server=None,port=None):
		if self.jid.node or self.jid.resource:
			raise ComponentStreamError,"Component JID may have only domain defined"
		if not server:
			server=self.server
		if not port:
			port=self.port
		if not server or not port:
			raise ComponentStreamError,"Server or port not given"
		Stream._connect(self,server,port,None,self.jid)

	def accept(self,sock):
		Stream.accept(self,sock,None)

	def _post_connect(self):
		if self.initiator:
			self._auth()

	def _compute_handshake(self):
		return sha.new(to_utf8(self.stream_id)+to_utf8(self.secret)).hexdigest()

	def _auth(self):
		if self.authenticated:
			self.debug("_auth: already authenticated")
			return
		self.debug("doing handshake...")
		hash=self._compute_handshake()
		n=common_doc.newTextChild(None,"handshake",hash)
		self._write_node(n)
		n.unlinkNode()
		n.freeNode()
	
	def _process_node(self,node):
		ns=node.ns()
		if ns:
			ns_uri=node.ns().getContent()
		if (not ns or ns_uri=="jabber:component:accept") and node.name=="handshake":
			if self.initiator and not self.authenticated:
				self.authenticated=1
				self.state_change("authenticated",self.jid)
				self._post_auth()
				return
			elif not self.authenticated and node.getContent()==self._compute_handshake():
				self.peer=self.me
				n=common_doc.newChild(None,"handshake",None)
				self._write_node(n)
				n.unlinkNode()
				n.freeNode()
				self.peer_authenticated=1
				self.state_change("authenticated",self.peer)
				self._post_auth()
				return
			else:
				self._send_stream_error("not-authorized")
				raise FatalComponentStreamError,"Hanshake error."

		if ns_uri in ("jabber:component:accept","jabber:client","jabber:server"):
			stanza=StanzaFactory(node)
			self.lock.release()
			try:
				self.process_stanza(stanza)
			finally:
				self.lock.acquire()
				stanza.free()
			return
		return Stream._process_node(self,node)
