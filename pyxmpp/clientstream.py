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

from stream import Stream,StreamError,FatalStreamError,SASLNotAvailable,SASLMechanismNotAvailable
from stream import StreamAuthenticationError
from iq import Iq
from stanza import common_doc
from jid import JID
from utils import to_utf8,from_utf8

class ClientStreamError(StreamError):
	pass

class FatalClientStreamError(FatalStreamError):
	pass

class LegacyAuthenticationError(StreamAuthenticationError):
	pass

class ClientStream(Stream):
	def __init__(self,jid,password=None,server=None,port=5222,
			auth_methods=["sasl:DIGEST-MD5"],
			tls_settings=None,keepalive=0):
		sasl_mechanisms=[]
		for m in auth_methods:
			if not m.startswith("sasl:"):
				continue
			m=m[5:].upper()
			sasl_mechanisms.append(m)
		Stream.__init__(self,"jabber:client",
					sasl_mechanisms=sasl_mechanisms,
					tls_settings=tls_settings,
					keepalive=keepalive)
		if server:
			self.server=server
		else:
			self.server=jid.domain
		self.port=port
		self.jid=jid
		self.password=password
		self.auth_methods=auth_methods
	
	def _reset(self):
		Stream._reset(self)
		self.auth_methods_left=[]

	def connect(self,server=None,port=None):
		self.lock.acquire()
		try:
			self._connect(server,port)
		finally:
			self.lock.release()
		
	def _connect(self,server=None,port=None):
		if not self.jid.node or not self.jid.resource:
			raise ClientStreamError,"Client JID must have username and resource"
		if server:
			self.server=server
		if port:
			self.port=port
		Stream._connect(self,self.server,self.port,self.jid.domain)

	def accept(self,sock):
		Stream.accept(self,sock,self.jid)

	def _post_connect(self):
		if self.initiator:
			self.auth_methods_left=list(self.auth_methods)
			self._try_auth()

	def _post_auth(self):
		if not self.initiator:
			self.unset_iq_get_handler("query","jabber:iq:auth")
			self.unset_iq_set_handler("query","jabber:iq:auth")

	def _try_auth(self):
		if self.authenticated:
			self.debug("try_auth: already authenticated")
			return
		self.debug("trying auth: %r" % (self.auth_methods_left,))
		if not self.auth_methods_left:
			raise LegacyAuthenticationError,"No allowed authentication methods available"
		method=self.auth_methods_left[0]
		if method.startswith("sasl:"):
			if self.version:
				self.auth_methods_left.pop(0)
				try:
					self._sasl_authenticate(self.jid.node,self.jid.as_unicode(),
								mechanism=method[5:].upper())
				except (SASLMechanismNotAvailable,SASLNotAvailable),e:
					self.debug("Skipping unavailable auth method: %s" % (method,) )
					return self._try_auth()
			else:
				self.auth_methods_left.pop(0)
				self.debug("Skipping auth method %s as legacy protocol is in use" % (method,) )
				return self._try_auth()
		else:
			self.auth_methods_left.pop(0)
			self.debug("Skipping unknown auth method: %s" % method)
			return self._try_auth()

	def get_password(self,username,realm=None,acceptable_formats=("plain",)):
		if self.initiator and self.jid.node==username and "plain" in acceptable_formats:
			return self.password,"plain"
		else:
			return None,None
	
	def get_realms(self):
		return [self.jid.domain]
	
	def choose_realm(self,realm_list):
		if not realm_list:
			return realm_list
		if self.jid.domain in realm_list:
			return self.jid.domain
		return realm_list[0]
			
	def check_authzid(self,authzid,extra_info={}):
		if not self.initiator:
			jid=JID(authzid)
			if not extra_info.has_key("username"):
				return 0
			if jid.node!=extra_info["username"]:
				return 0
			if jid.domain!=self.jid.domain:
				return 0
			if not jid.resource:
				return 0
			return 1
		return 0

	def get_serv_type(self):
		return "xmpp"
	
	def get_serv_name(self):
		return self.jid.domain
			
	def get_serv_host(self):
		return self.jid.domain

	def fix_out_stanza(self,stanza):
		if self.initiator:
			stanza.set_from(None)
		else:
			if not stanza.get_from():
				stanza.set_from(self.me)
	
	def fix_in_stanza(self,stanza):
		if self.initiator:
			Stream.fix_in_stanza(self,stanza)
		else:
			stanza.set_from(self.peer)
