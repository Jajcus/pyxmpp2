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
from pyxmpp.stream import StreamAuthenticationError
from pyxmpp.iq import Iq
from pyxmpp.stanza import common_doc
from pyxmpp.jid import JID
from pyxmpp.utils import to_utf8,from_utf8

from pyxmpp.clientstream import ClientStreamError,FatalClientStreamError,LegacyAuthenticationError
from pyxmpp.clientstream import ClientStream

class LegacyClientStream(ClientStream):
	def __init__(self,jid,password=None,server=None,port=5222,
			auth_methods=["sasl:DIGEST-MD5","digest"],
			tls_settings=None,keepalive=0):

		ClientStream.__init__(self,jid,password,server,port,
							auth_methods,tls_settings,keepalive)
	
	def _reset(self):
		ClientStream._reset(self)
		self.available_auth_methods=None
		self.auth_stanza=None

	def _post_connect(self):
		if not self.initiator:
			if "plain" in self.auth_methods or "digest" in self.auth_methods:
				self.set_iq_get_handler("query","jabber:iq:auth",
							self.auth_in_stage1)
				self.set_iq_set_handler("query","jabber:iq:auth",
							self.auth_in_stage2)
		ClientStream._post_connect(self)

	def _post_auth(self):
		ClientStream._post_auth(self)
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
			return ClientStream._try_auth(self)
		elif method not in ("plain","digest"):
			self.auth_methods_left.pop(0)
			self.debug("Skipping unknown auth method: %s" % method)
			return self._try_auth()
		elif self.available_auth_methods is not None:
			if method in self.available_auth_methods:
				self.auth_methods_left.pop(0)
				self.auth_method_used=method
				if method=="digest":
					self._digest_auth_stage2(self.auth_stanza)
				else:
					self._plain_auth_stage2(self.auth_stanza)
				self.auth_stanza=None
				return
			else:
				self.debug("Skipping unavailable auth method: %s" % method)
		else:
			self._auth_stage1()

	def auth_in_stage1(self,stanza):
		self.lock.acquire()
		try:
			if "plain" not in self.auth_methods and "digest" not in self.auth_methods:
				iq=stanza.make_error_response("not-allowed")
				self.send(iq)
				return

			iq=stanza.make_result_response()
			q=iq.new_query("jabber:iq:auth")
			q.newChild(q.ns(),"username",None)
			q.newChild(q.ns(),"resource",None)
			if "plain" in self.auth_methods:
				q.newChild(q.ns(),"password",None)
			if "digest" in self.auth_methods:
				q.newChild(q.ns(),"digest",None)
			self.send(iq)
			iq.free()
		finally:
			self.lock.release()

	def auth_in_stage2(self,stanza):
		self.lock.acquire()
		try:
			if "plain" not in self.auth_methods and "digest" not in self.auth_methods:
				iq=stanza.make_error_response("not-allowed")
				self.send(iq)
				return
		
			username=stanza.xpath_eval("a:query/a:username",{"a":"jabber:iq:auth"})
			if username:
				username=from_utf8(username[0].getContent())
			resource=stanza.xpath_eval("a:query/a:resource",{"a":"jabber:iq:auth"})
			if resource:
				resource=from_utf8(resource[0].getContent())
			if not username or not resource:
				self.debug("No username or resource found in auth request")
				iq=stanza.make_error_response("bad-request")
				self.send(iq)
				return

			if stanza.xpath_eval("a:query/a:password",{"a":"jabber:iq:auth"}):
				if "plain" not in self.auth_methods:
					iq=stanza.make_error_response("not-allowed")
					self.send(iq)
					return
				else:
					return self._plain_auth_in_stage2(username,resource,stanza)
			if stanza.xpath_eval("a:query/a:digest",{"a":"jabber:iq:auth"}):
				if "plain" not in self.auth_methods:
					iq=stanza.make_error_response("not-allowed")
					self.send(iq)
					return
				else:
					return self._digest_auth_in_stage2(username,resource,stanza)
		finally:
			self.lock.release()

	def _auth_stage1(self):
		iq=Iq(type="get")
		q=iq.new_query("jabber:iq:auth")
		q.newChild(q.ns(),"username",to_utf8(self.jid.node))
		q.newChild(q.ns(),"resource",to_utf8(self.jid.resource))
		self.send(iq)
		self.set_response_handlers(iq,self.auth_stage2,self.auth_error,
							self.auth_timeout,timeout=60)
		iq.free()
		
	def auth_timeout(self,*args):
		self.lock.acquire()
		try:
			self.debug("Timeout while waiting for jabber:iq:auth result")
			if self.auth_methods_left:
				self.auth_methods_left.pop(0)
		finally:
			self.lock.release()
	
	def auth_error(self,stanza):
		self.lock.acquire()
		try:
			err=stanza.get_error()
			ae=err.xpath_eval("e:*",{"e":"jabber:iq:auth:error"})
			if ae:
				ae=ae[0].name
			else:
				ae=err.get_condition().name
			raise LegacyAuthenticationError,("Athentication error condition: %s" 
						% (ae,))
		finally:
			self.lock.release()

	def auth_stage2(self,stanza):
		self.lock.acquire()
		try:
			self.debug("Procesing auth response...")
			self.available_auth_methods=[]
			if (stanza.xpath_eval("a:query/a:digest",{"a":"jabber:iq:auth"}) and self.stream_id):
						self.available_auth_methods.append("digest")
			if (stanza.xpath_eval("a:query/a:password",{"a":"jabber:iq:auth"})):
						self.available_auth_methods.append("plain")
			self.auth_stanza=stanza.copy()
			self.try_auth()
		finally:
			self.lock.release()
	
	def _plain_auth_stage2(self,stanza):
		iq=Iq(type="set")
		q=iq.new_query("jabber:iq:auth")
		q.newChild(None,"username",to_utf8(self.jid.node))
		q.newChild(None,"resource",to_utf8(self.jid.resource))
		q.newChild(None,"password",to_utf8(self.password))
		self.send(iq)
		self.set_response_handlers(iq,self.auth_finish,self.auth_error)
		iq.free()
	
	def _plain_auth_in_stage2(self,username,resource,stanza):
		password=stanza.xpath_eval("a:query/a:password",{"a":"jabber:iq:auth"})
		if password:
			password=from_utf8(password[0].getContent())
		if not password:
			self.debug("No password found in plain auth request")
			iq=stanza.make_error_response("bad-request")
			self.send(iq)
			return

		if self.check_password(username,password):
			iq=stanza.make_result_response()
			self.send(iq)
			self.peer_authenticated=1
			self.auth_method_used="plain"
			self.state_change("authenticated",self.peer)
			self.post_auth()
		else:
			self.debug("Plain auth failed")
			iq=stanza.make_error_response("bad-request")
			e=iq.get_error()
			e.add_custom_condition('jabber:iq:auth:error',"user-unauthorized")
			self.send(iq)
	
	def _digest_auth_stage2(self,stanza):
		iq=Iq(type="set")
		q=iq.new_query("jabber:iq:auth")
		q.newChild(None,"username",to_utf8(self.jid.node))
		q.newChild(None,"resource",to_utf8(self.jid.resource))
		digest=sha.new(to_utf8(self.stream_id)+to_utf8(self.password)).hexdigest()
		q.newChild(None,"digest",digest)
		self.send(iq)
		self.set_response_handlers(iq,self.auth_finish,self.auth_error)
		iq.free()
	
	def _digest_auth_in_stage2(self,username,resource,stanza):
		digest=stanza.xpath_eval("a:query/a:digest",{"a":"jabber:iq:auth"})
		if digest:
			digest=digest[0].getContent()
		if not digest:
			self.debug("No digest found in digest auth request")
			iq=stanza.make_error_response("bad-request")
			self.send(iq)
			return
		
		password,pwformat=self.get_password(username)
		if not password or pwformat!="plain":
			iq=stanza.make_error_response("bad-request")
			e=iq.get_error()
			e.add_custom_condition('jabber:iq:auth:error',"user-unauthorized")
			self.send(iq)
			return
			
		mydigest=sha.new(to_utf8(self.stream_id)+to_utf8(password)).hexdigest()

		if mydigest==digest:
			iq=stanza.make_result_response()
			self.send(iq)
			self.peer_authenticated=1
			self.auth_method_used="digest"
			self.state_change("authenticated",self.peer)
			self.post_auth()
		else:
			self.debug("Digest auth failed: %r != %r" % (digest,mydigest))
			iq=stanza.make_error_response("bad-request")
			e=iq.get_error()
			e.add_custom_condition('jabber:iq:auth:error',"user-unauthorized")
			self.send(iq)
	
	def auth_finish(self,stanza):
		self.lock.acquire()
		try:
			self.debug("Authenticated")
			self.me=self.jid
			self.authenticated=1
			self.state_change("authenticated",self.me)
			self.post_auth()
		finally:
			self.lock.release()
