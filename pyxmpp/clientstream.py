
import libxml2
import sha
from types import UnicodeType

import stream
from iq import Iq
from stanza import common_doc
from jid import JID
from utils import to_utf8,from_utf8

class ClientError(RuntimeError):
	pass

class AuthenticationError(ClientError):
	pass

class ClientStream(stream.Stream):
	def __init__(self,jid,password=None,server=None,port=5222,
			auth_methods=["sasl:DIGEST-MD5","digest","plain"],
			enable_tls=0,require_tls=0):
		sasl_mechanisms=[]
		for m in auth_methods:
			if not m.startswith("sasl:"):
				continue
			m=m[5:].upper()
			sasl_mechanisms.append(m)
		stream.Stream.__init__(self,"jabber:client",
					sasl_mechanisms=sasl_mechanisms,
					enable_tls=enable_tls,
					require_tls=require_tls)
		if server:
			self.server=server
		else:
			self.server=jid.domain
		self.port=port
		self.jid=jid
		self.peer_jid=None
		self.password=password
		self.auth_methods=auth_methods
		self._authenticated=0
		self._peer_authenticated=0

	def connect(self,server=None,port=None):
		if not self.jid.node or not self.jid.resource:
			raise ClientError,"Client JID must have username and resource"
		if server:
			self.server=server
		if port:
			self.port=port
		stream.Stream.connect(self,self.server,self.port,self.jid.domain)

	def accept(self,sock):
		stream.Stream.accept(self,sock,self.jid)

	def post_connect(self):
		if self.initiator:
			self.peer_jid=JID(self.peer)
			#self.auth_stage1()
			self.sasl_authorize(self.jid.node,self.jid.as_unicode())
		else:
			self.set_iq_get_handler("query","jabber:iq:auth",self.auth_in_stage1)
			self.set_iq_set_handler("query","jabber:iq:auth",self.auth_in_stage2)

	def post_disconnect(self):
		self._authenticated=0

	def auth_in_stage1(self,stanza):
		if "plain" not in self.auth_methods and "digest" not in self.auth_methods:
			iq=stanza.make_error_reply("access","forbidden")
			self.send(iq)
			return

		iq=stanza.make_result_reply()
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
			iq=stanza.make_error_reply("access","forbidden")
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
			iq=stanza.make_error_reply("format","bad-request")
			self.send(iq)
			return

		if stanza.xpath_eval("a:query/a:password",{"a":"jabber:iq:auth"}):
			if "plain" not in self.auth_methods:
				iq=stanza.make_error_reply("access","forbidden")
				self.send(iq)
				return
			else:
				return self.plain_auth_in_stage2(username,resource,stanza)
		if stanza.xpath_eval("a:query/a:digest",{"a":"jabber:iq:auth"}):
			if "plain" not in self.auth_methods:
				iq=stanza.make_error_reply("access","forbidden")
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
		self.set_reply_handlers(iq,self.auth_stage2,self.auth_error)
		iq.free()
		
	def auth_error(self,stanza):
		err=stanza.get_error()
		raise AuthenticationError,("Athentication error class=%r condition=%r" 
					% (err.get_class(), err.get_condition().serialize()))
	def auth_stage2(self,stanza):
		print "Procesing auth reply..."
		
		for m in self.auth_methods:
			if (m=="digest" 
				and stanza.xpath_eval("a:query/a:digest",{"a":"jabber:iq:auth"})
				and self.stream_id):
					return self.digest_auth_stage2(stanza)
			if (m=="plain" 
				and stanza.xpath_eval("a:query/a:password",{"a":"jabber:iq:auth"})):
					return self.plain_auth_stage2(stanza)
		raise AuthenticationError,"No allowed authentication method supported"
	
	def plain_auth_stage2(self,stanza):
		iq=Iq(type="set")
		q=iq.new_query("jabber:iq:auth")
		q.newChild(None,"username",to_utf8(self.jid.node))
		q.newChild(None,"resource",to_utf8(self.jid.resource))
		q.newChild(None,"password",to_utf8(self.password))
		self.send(iq)
		self.set_reply_handlers(iq,self.auth_finish,self.auth_error)
		iq.free()
	
	def plain_auth_in_stage2(self,username,resource,stanza):
		password=stanza.xpath_eval("a:query/a:password",{"a":"jabber:iq:auth"})
		if password:
			password=from_utf8(password[0].getContent())
		if not password:
			self.debug("No password found in plain auth request")
			iq=stanza.make_error_reply("format","bad-request")
			self.send(iq)
			return

		if self.check_password(username,password):
			iq=stanza.make_result_reply()
			self.send(iq)
		else:
			iq=stanza.make_error_reply("access",
				('jabber:iq:auth:error',"user-unauthorized",None))
			self.send(iq)
	
	def digest_auth_stage2(self,stanza):
		iq=Iq(type="set")
		q=iq.new_query("jabber:iq:auth")
		q.newChild(None,"username",to_utf8(self.jid.node))
		q.newChild(None,"resource",to_utf8(self.jid.resource))
		digest=sha.new(to_utf8(self.stream_id)+to_utf8(self.password)).hexdigest()
		q.newChild(None,"digest",digest)
		self.send(iq)
		self.set_reply_handlers(iq,self.auth_finish,self.auth_error)
		iq.free()
	
	def digest_auth_in_stage2(self,username,resource,stanza):
		digest=stanza.xpath_eval("a:query/a:digest",{"a":"jabber:iq:auth"})
		if digest:
			digest=digest[0].getContent()
		if not digest:
			self.debug("No digest found in digest auth request")
			iq=stanza.make_error_reply("format","bad-request")
			self.send(iq)
			return
		
		password=self.get_password(username)
		if not password:
			iq=stanza.make_error_reply("access",
				('jabber:iq:auth:error',"user-unauthorized",None))
			self.send(iq)
			return
			
		mydigest=sha.new(to_utf8(self.stream_id)+to_utf8(password)).hexdigest()

		if mydigest==digest:
			iq=stanza.make_result_reply()
			self.send(iq)
		else:
			iq=stanza.make_error_reply("access",
				('jabber:iq:auth:error',"user-unauthorized",None))
			self.send(iq)
	
	def auth_finish(self,stanza):
		print "Authenticated"
		self._authenticated=1
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
			
	def post_auth(self):
		pass

	def authenticated(self):
		return self._authenticated
	
	def peer_authenticated(self):
		return self._peer_authenticated
