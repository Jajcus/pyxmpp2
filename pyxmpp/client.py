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
import sys

from clientstream import ClientStream
from jid import JID
from iq import Iq
from utils import to_utf8,from_utf8

class ClientError(StandardError):
	pass

class Client:
	def __init__(self,jid=None,password=None,server=None,port=5222,
			auth_methods=["sasl:DIGEST-MD5","digest"],
			enable_tls=0,require_tls=0):

		self.jid=jid
		self.password=password
		self.server=server
		self.port=port
		self.auth_methods=auth_methods
		self.enable_tls=0
		self.require_tls=0
		self.stream=None
		self.session_established=0

# public methods

	def connect(self,register=0):
		if not self.jid:
			raise ClientError,"Cannot connect: no or bad JID given"
		if not register and not self.password:
			raise ClientError,"Cannot connect: no password given"
		if register:
			raise ClientError,"In-band registration not implemented yet"
		if self.stream:
			self.stream.close()
			
		self.stream=ClientStream(self.jid,self.password,self.server,
			self.port,self.auth_methods,self.enable_tls,self.require_tls)
		self.stream.debug=self.debug
		self.stream.connect()
		self.stream.post_auth=self.__post_auth

	def disconnect(self):
		if self.stream:
			self.stream.disconnect()

	def request_session(self):
		if not self.stream.version:
			self.session_established=1
			self.session_started()
		else:
			iq=Iq(type="set")
			iq.new_query("urn:ietf:params:xml:ns:xmpp-session","session")
			self.stream.set_response_handlers(iq,
				self.__session_result,self.__session_error,self.__session_timeout)
			self.stream.send(iq)

	def socket(self):
		return self.stream.socket

	def loop(self,timeout=1):
		self.stream.loop(timeout)

# private methods
	
	def __session_timeout(self,k,v):
		raise FatalClientError("Timeout while tryin to establish a session")
		
	def __session_error(self,iq):
		raise FatalClientError("Failed establish session")
	
	def __session_result(self,iq):
		self.session_established=1
		self.session_started()
	
	def __post_auth(self):
		ClientStream.post_auth(self.stream)
		self.post_auth()
		
# Method to override
	def idle(self):
		if self.stream:
			self.stream.idle()

	def session_started(self):
		pass

	def post_auth(self):
		self.request_session()

	def debug(self,str):
		print >>sys.stderr,"DEBUG:",str

