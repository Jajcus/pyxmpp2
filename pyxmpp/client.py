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
import threading

from clientstream import ClientStream
from jid import JID
from iq import Iq
from presence import Presence
from utils import to_utf8,from_utf8
from roster import Roster

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
		self.stream_cond=threading.Condition()
		self.session_established=0
		self.roster=None

# public methods

	def connect(self,register=0):
		if not self.jid:
			raise ClientError,"Cannot connect: no or bad JID given"
		if not register and not self.password:
			raise ClientError,"Cannot connect: no password given"
		if register:
			raise ClientError,"In-band registration not implemented yet"

		self.stream_cond.acquire()
		stream=self.stream
		self.stream=None
		if stream:
			stream.close()
		self.stream_cond.notify()
		self.stream_cond.release()
			
		stream=ClientStream(self.jid,self.password,self.server,
			self.port,self.auth_methods,self.enable_tls,self.require_tls)
		stream.debug=self.debug
		stream.print_exception=self.print_exception
		stream.connect()
		stream.post_auth=self.__post_auth
		self.stream_cond.acquire()
		self.stream=stream
		self.stream_cond.notify()
		self.stream_cond.release()

	def get_stream(self):
		self.stream_cond.acquire()
		stream=self.stream
		self.stream_cond.release()
		return stream

	def disconnect(self):
		stream=self.get_stream()
		if stream:
			stream.disconnect()

	def request_session(self):
		stream=self.get_stream()
		if not stream.version:
			self.session_established=1
			self.session_started()
		else:
			iq=Iq(type="set")
			iq.new_query("urn:ietf:params:xml:ns:xmpp-session","session")
			stream.set_response_handlers(iq,
				self.__session_result,self.__session_error,self.__session_timeout)
			stream.send(iq)
	
	def request_roster(self):
		stream=self.get_stream()
		iq=Iq(type="get")
		iq.new_query("jabber:iq:roster")
		stream.set_response_handlers(iq,
			self.__roster_result,self.__roster_error,self.__roster_timeout)
		stream.set_iq_set_handler("query","jabber:iq:roster",self.__roster_push)
		stream.send(iq)

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
	
	def __roster_timeout(self,k,v):
		raise ClientError("Timeout while tryin to retrieve roster")
		
	def __roster_error(self,iq):
		raise ClientError("Roster retrieval failed")
	
	def __roster_result(self,iq):
		q=iq.get_query()
		if q:
			self.roster=Roster(q)
			self.roster_updated()
		else:
			raise ClientError("Roster retrieval failed")

	def __roster_push(self,iq):
		fr=iq.get_from()
		if fr and fr!=self.jid:
			resp=iq.make_error_response("forbidden")
			self.stream.send(resp)
			raise ClientError("Got roster update from wrong source")
		if not self.roster:
			raise ClientError("Roster update, but no roster")
		q=iq.get_query()
		item=self.roster.update(q)
		if item:
			self.roster_updated(item.jid())
		resp=iq.make_result_response()
		self.stream.send(resp)
	
	def __post_auth(self):
		ClientStream.post_auth(self.stream)
		self.post_auth()
		
# Method to override
	def idle(self):
		stream=self.get_stream()
		if stream:
			stream.idle()

	def session_started(self):
		p=Presence()
		self.stream.send(p)
		self.request_roster()

	def roster_updated(self):
		pass

	def post_auth(self):
		self.request_session()

	def debug(self,str):
		print >>sys.stderr,"DEBUG:",str

	def print_exception(self):
		for s in traceback.format_exception(sys.exc_type,sys.exc_value,sys.exc_traceback):
			if s[-1]=='\n':
				s=s[:-1]
			self.debug(s)
