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

class ClientError(StreamError):
	pass

class FatalClientError(FatalStreamError):
	pass

class LegacyAuthenticationError(StreamAuthenticationError):
	pass

class ClientStream(Stream):
	def __init__(self,jid,password=None,server=None,port=5222,
			auth_methods=["sasl:DIGEST-MD5","digest"],
			enable_tls=0,require_tls=0):
		sasl_mechanisms=[]
		for m in auth_methods:
			if not m.startswith("sasl:"):
				continue
			m=m[5:].upper()
			sasl_mechanisms.append(m)
		Stream.__init__(self,"jabber:client",
					sasl_mechanisms=sasl_mechanisms,
					enable_tls=enable_tls,
					require_tls=require_tls)
		if server:
			self.server=server
		else:
			self.server=jid.domain
		self.port=port
		self.jid=jid
		self.password=password
		self.auth_methods=auth_methods
	
	def reset(self):
		Stream.reset(self)
		self.auth_methods_left=[]
		self.session_established=1
		self.available_auth_methods=None
		self.features_timeout=None
		self.auth_stanza=None

	def connect(self,server=None,port=None):
		if not self.jid.node or not self.jid.resource:
			raise ClientError,"Client JID must have username and resource"
		if server:
			self.server=server
		if port:
			self.port=port
		Stream.connect(self,self.server,self.port,self.jid.domain)

	def accept(self,sock):
		Stream.accept(self,sock,self.jid)

	def post_connect(self):
		if self.initiator:
			self.auth_methods_left=self.auth_methods
			self.try_auth()
		else:
			if "plain" in self.auth_methods or "digest" in self.auth_methods:
				self.set_iq_get_handler("query","jabber:iq:auth",
							self.auth_in_stage1)
				self.set_iq_set_handler("query","jabber:iq:auth",
							self.auth_in_stage2)

	def post_auth(self):
		if not self.initiator:
			self.unset_iq_get_handler("query","jabber:iq:auth")
			self.unset_iq_set_handler("query","jabber:iq:auth")

	def request_session(self):
		if not self.version:
			self.session_established=1
			self.session_started()
		else:
			iq=Iq(type="set")
			iq.new_query("urn:ietf:params:xml:ns:xmpp-session","session")
			self.set_response_handlers(iq,self.session_result,self.session_error)
			self.send(iq)
		
	def session_timeout(self,k,v):
		raise FatalClientError("Timeout while tryin to establish a session")
		
	def session_error(self,iq):
		raise FatalClientError("Failed establish session")
	
	def session_result(self,iq):
		self.session_established=1
		self.session_started()
	
	def session_started(self):
		pass

	def idle(self):
		Stream.idle(self)
		if self.features_timeout and self.features_timeout<=time.time():
			self.debug("Timout while waiting for <features/>")
			self.features_timeout=None
			if self.auth_methods_left:
				self.auth_methods_left.pop(0)
			self.try_auth()

	def got_features(self):
		self.debug("Got <features/>")
		Stream.got_features(self)
		self.try_auth()

	def try_auth(self):
		if self.authenticated:
			self.debug("try_auth: already authenticated")
			return
		self.features_timeout=None
		self.debug("trying auth: %r" % (self.auth_methods_left,))
		if not self.auth_methods_left:
			raise AuthenticationError,"No allowed authentication methods available"
		method=self.auth_methods_left[0]
		if method.startswith("sasl:"):
			if self.features:
				self.auth_methods_left.pop(0)
				try:
					self.sasl_authenticate(self.jid.node,self.jid.as_unicode(),
								mechanism=method[5:].upper())
				except (SASLMechanismNotAvailable,SASLNotAvailable),e:
					self.debug("Skipping unavailable auth method: %s" % (method,) )
					return self.try_auth()
			elif not self.version:
				self.auth_methods_left.pop(0)
				self.debug("Skipping auth method %s as legacy protocol is in use" % (method,) )
				return self.try_auth()
			else:
				self.features_timeout=time.time()+60
				self.debug("Must wait for <features/>")
				return
		elif method not in ("plain","digest"):
			self.debug("Skipping unknown auth method: %s" % method)
			return self.try_auth()
		elif self.available_auth_methods is not None:
			if method in self.available_auth_methods:
				self.auth_methods_left.pop(0)
				self.auth_method_used=method
				if method=="digest":
					self.digest_auth_stage2(self.auth_stanza)
				else:
					self.plain_auth_stage2(self.auth_stanza)
				self.auth_stanza=None
				return
			else:
				self.debug("Skipping unavailable auth method: %s" % method)
		else:
			self.auth_stage1()

	def auth_in_stage1(self,stanza):
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

	def auth_in_stage2(self,stanza):
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
				return self.plain_auth_in_stage2(username,resource,stanza)
		if stanza.xpath_eval("a:query/a:digest",{"a":"jabber:iq:auth"}):
			if "plain" not in self.auth_methods:
				iq=stanza.make_error_response("not-allowed")
				self.send(iq)
				return
			else:
				return self.digest_auth_in_stage2(username,resource,stanza)

	def auth_stage1(self):
		iq=Iq(type="get")
		q=iq.new_query("jabber:iq:auth")
		q.newChild(q.ns(),"username",to_utf8(self.jid.node))
		q.newChild(q.ns(),"resource",to_utf8(self.jid.resource))
		self.send(iq)
		self.set_response_handlers(iq,self.auth_stage2,self.auth_error,
							self.features_timeout,timeout=60)
		iq.free()
		
	def features_timeout(self,*args):
		debug("Timeout while waiting for jabber:iq:auth result")
		if self.auth_methods_left:
			self.auth_methods_left.pop(0)
	
	def auth_error(self,stanza):
		err=stanza.get_error()
		raise AuthenticationError,("Athentication error class=%r condition=%r" 
					% (err.get_class(), err.get_condition().serialize()))

	def auth_stage2(self,stanza):
		print "Procesing auth response..."
	
		self.available_auth_methods=[]
		if (stanza.xpath_eval("a:query/a:digest",{"a":"jabber:iq:auth"}) and self.stream_id):
					self.available_auth_methods.append("digest")
		if (stanza.xpath_eval("a:query/a:password",{"a":"jabber:iq:auth"})):
					self.available_auth_methods.append("plain")
		self.auth_stanza=stanza.copy()
		self.try_auth()
	
	def plain_auth_stage2(self,stanza):
		iq=Iq(type="set")
		q=iq.new_query("jabber:iq:auth")
		q.newChild(None,"username",to_utf8(self.jid.node))
		q.newChild(None,"resource",to_utf8(self.jid.resource))
		q.newChild(None,"password",to_utf8(self.password))
		self.send(iq)
		self.set_response_handlers(iq,self.auth_finish,self.auth_error)
		iq.free()
	
	def plain_auth_in_stage2(self,username,resource,stanza):
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
			self.post_auth()
		else:
			self.debug("Plain auth failed")
			iq=stanza.make_error_response("bad-request")
			e=iq.get_error()
			e.add_custom_condition('jabber:iq:auth:error',"user-unauthorized")
			self.send(iq)
	
	def digest_auth_stage2(self,stanza):
		iq=Iq(type="set")
		q=iq.new_query("jabber:iq:auth")
		q.newChild(None,"username",to_utf8(self.jid.node))
		q.newChild(None,"resource",to_utf8(self.jid.resource))
		digest=sha.new(to_utf8(self.stream_id)+to_utf8(self.password)).hexdigest()
		q.newChild(None,"digest",digest)
		self.send(iq)
		self.set_response_handlers(iq,self.auth_finish,self.auth_error)
		iq.free()
	
	def digest_auth_in_stage2(self,username,resource,stanza):
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
			self.post_auth()
		else:
			self.debug("Digest auth failed: %r != %r" % (digest,mydigest))
			iq=stanza.make_error_response("bad-request")
			e=iq.get_error()
			e.add_custom_condition('jabber:iq:auth:error',"user-unauthorized")
			self.send(iq)
	
	def auth_finish(self,stanza):
		print "Authenticated"
		self.me=self.jid
		self.authenticated=1
		self.post_auth()

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
			if not stanza.get_to() and self.peer:
				stanza.set_to(self.peer)
		else:
			Stream.fix_out_stanza(self,stanza)
	
		
