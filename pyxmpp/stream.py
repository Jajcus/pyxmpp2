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
import xmlextra
import socket
import os
import sys
import time
import random
import base64
import traceback

from expdict import ExpiringDictionary
from utils import from_utf8,to_utf8
from stanza import Stanza,common_doc,StanzaError
from error import StreamErrorNode
from iq import Iq
from presence import Presence
from message import Message
from jid import JID
import sasl

STREAM_NS="http://etherx.jabber.org/streams"
TLS_NS="urn:ietf:params:xml:ns:xmpp-tls"
SASL_NS="urn:ietf:params:xml:ns:xmpp-sasl"

class StreamError(StandardError):
	pass

class StreamEncryptionRequired(StreamError):
	pass

class HostMismatch(StreamError):
	pass

class FatalStreamError(StreamError):
	pass

class StreamParseError(FatalStreamError):
	pass

class StreamAuthenticationError(FatalStreamError):
	pass

class SASLNotAvailable(StreamAuthenticationError):
	pass

class SASLMechanismNotAvailable(StreamAuthenticationError):
	pass

class SASLAuthenticationFailed(StreamAuthenticationError):
	pass


def StanzaFactory(node):
	if node.name=="iq":
		return Iq(node)
	if node.name=="message":
		return Message(node)
	if node.name=="presence":
		return Presence(node)
	else:
		return Stanza(node)

class Stream(sasl.PasswordManager,xmlextra.StreamHandler):
	def __init__(self,default_ns,extra_ns=[],sasl_mechanisms=[],
					enable_tls=0,require_tls=0,keepalive=0):
		self.default_ns_uri=default_ns
		self.extra_ns_uris=extra_ns
		self.sasl_mechanisms=sasl_mechanisms
		self.enable_tls=enable_tls
		self.require_tls=require_tls
		self.keepalive=keepalive
		self.reset()

	def reset(self):
		self.doc_in=None
		self.doc_out=None
		self.socket=None
		self.reader=None
		self.addr=None
		self.port=None
		self.default_ns=None
		self.peer_sasl_mechanisms=None
		self.extra_ns={}
		self.stream_ns=None
		self.reader=None
		self.ioreader=None
		self.me=None
		self.peer=None
		self.skip=0
		self.stream_id=None
		self.iq_response_handlers=ExpiringDictionary()
		self.iq_get_handlers={}
		self.iq_set_handlers={}
		self.message_handlers=[]
		self.presence_handlers=[]
		self.eof=0
		self.initiator=None
		self.features=None
		self.tls=0
		self.authenticator=None
		self.authenticated=0
		self.peer_authenticated=0
		self.auth_method_used=None
		self.version=None
		self.last_keepalive=0

	def __del__(self):
		self.close()

	def connect_socket(self,sock,to=None):
		self.eof=0
		self.socket=sock
		if to:
			self.peer=JID(to)
		else:
			self.peer=None
		self.initiator=1
		self.send_stream_start()
		self.make_reader()

	def connect(self,addr,port,to=None):
		if to is None:
			to=str(addr)
		s=socket.socket()
		s.connect((addr,port))
		self.addr=addr
		self.port=port
		self.connect_socket(s,to)
		self.last_keepalive=time.time()

	def accept(self,sock,myname):
		self.eof=0
		self.socket,addr=sock.accept()
		self.debug("Connection from: %r" % (addr,))
		self.addr,self.port=addr
		if myname:
			self.me=JID(myname)
		else:
			self.me=None
		self.initiator=0
		self.make_reader()
		self.last_keepalive=time.time()

	def disconnect(self):
		if self.doc_out:
			self.send_stream_end()

	def close(self):
		self.disconnect()
		if self.doc_in:
			self.doc_in=None
		if self.features:
			self.features=None
		self.reader=None
		self.stream_id=None
		if self.socket:
			self.socket.close()
		self.reset()

	def make_reader(self):
		self.reader=xmlextra.StreamReader(self)

	def stream_start(self,doc):
		self.doc_in=doc
		self.debug("input document: %r" % (self.doc_in.serialize(),))
	
		try:
			r=self.doc_in.getRootElement()
			if r.ns().getContent() != STREAM_NS:
				self.send_stream_error("invalid-namespace")
				raise FatalStreamError,"Invalid namespace."
		except libxml2.treeError:
			self.send_stream_error("invalid-namespace")
			raise FatalStreamError,"Couldn't get the namespace."
			

		self.version=r.prop("version")
		if self.version and self.version!="1.0":
			self.send_stream_error("unsupported-version")
			raise FatalStreamError,"Unsupported protocol version."
		
		to_from_mismatch=0
		if self.initiator:
			self.stream_id=r.prop("id")
			peer=r.prop("from")
			if peer:
				peer=JID(peer)
			if self.peer:
				if peer and peer!=self.peer:
					to_from_mismatch=1
			else:
				self.peer=peer
		else:
			to=r.prop("to")
			if to:
				to=self.check_to(to)
				if not to:
					self.send_stream_error("host-unknown")
					raise FatalStreamError,'Bad "to"'
				self.me=JID(to)
			self.send_stream_start(self.generate_id())
			self.send_stream_features()

		self.post_connect()
		if to_from_mismatch:
			raise HostMismatch

	def stream_end(self,doc):
		self.debug("Stream ended")
		self.eof=1
		if self.doc_out:
			self.send_stream_end()
		if self.doc_in:
			self.doc_in=None
			self.reader=None
			if self.features:
				self.features=None
		self.post_disconnect()

	def stanza_start(self,doc,node):
		pass

	def stanza_end(self,doc,node):
		self.process_node(node)

	def error(self,desc):
		raise StreamParseError,desc
				
	def send_stream_end(self):
		self.doc_out.getRootElement().addContent(" ")
		str=self.doc_out.getRootElement().serialize(encoding="UTF-8")
		end=str.rindex("<")
		try:
			self.write_raw(str[end:])
		except (IOError,SystemError),e:
			self.debug("Sending stream closing tag failed:"+str(e))
		self.doc_out.freeDoc()
		self.doc_out=None
		if self.features:
			self.features=None
		
	def send_stream_start(self,id=None):
		if self.doc_out:
			raise StreamError,"Stream start already sent"
		self.doc_out=libxml2.newDoc("1.0")
		root=self.doc_out.newChild(None, "stream", None)
		self.stream_ns=root.newNs(STREAM_NS,"stream")
		root.setNs(self.stream_ns)
		self.default_ns=root.newNs(self.default_ns_uri,None)
		for prefix,uri in self.extra_ns:
			self.extra_ns[uri]=root.newNs(uri,prefix)
		if self.peer:
			root.setProp("to",self.peer.as_string())
		if self.me:
			root.setProp("from",self.me.as_string())
		root.setProp("version","1.0")
		if id:
			root.setProp("id",id)
			self.stream_id=id
		sr=self.doc_out.serialize(encoding="UTF-8")
		self.write_raw(sr[:sr.find("/>")]+">")
	
	def send_stream_error(self,condition):
		if not self.doc_out:
			self.send_stream_start()
		e=StreamErrorNode(condition)
		e.node.setNs(self.stream_ns)
		self.write_raw(e.serialize())
		e.free()
		self.send_stream_end()

	def get_stream_features(self):
		root=self.doc_out.getRootElement()
		features=root.newChild(root.ns(),"features",None)
		if self.sasl_mechanisms:
			ml=features.newChild(None,"mechanisms",None)
			ns=ml.newNs(SASL_NS,None)
			ml.setNs(ns)
			for m in self.sasl_mechanisms:
				if m in sasl.all_mechanisms:
					ml.newChild(ns,"mechanism",m)
		if self.enable_tls and not self.tls:
			tls=features.newChild(None,"starttls",None)
			ns=tls.newNs(TLS_NS,None)
			tls.setNs(ns)
			if self.require_tls:
				tls.newChild(ns,"required",None)
		return features
		
	def send_stream_features(self):
		self.features=self.get_stream_features()
		self.write_raw(self.features.serialize(encoding="UTF-8"))

	def new_node(self,name,ns=None):
		if not ns:
			ns=self.default_ns
		return self.doc_out.newDocNode(ns,name,None)

	def write_raw(self,str):
		self.data_out(str)
		self.socket.send(str)

	def write_node(self,node):
		node=node.docCopyNode(self.doc_out,1)
		self.doc_out.addChild(node)
		#node.reconciliateNs(self.doc_out)
		self.write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()
		
	def send(self,stanza):
		if self.require_tls and not self.tls:
			raise StreamEncryptionRequired,"TLS encryption required and not started yet"
			
		if not self.version:
			try:
				err=stanza.get_error()
			except StanzaError:
				err=None
			if err:
				err.downgrade()
		self.fix_out_stanza(stanza)
		self.write_node(stanza.node)

	def eof_handler(self):
		self.eof=1

	def idle(self):
		self.iq_response_handlers.expire()
		if not self.socket or self.eof:
			return
		now=time.time()
		if self.keepalive and now-self.last_keepalive>=self.keepalive:
			self.write_raw(" ")
			self.last_keepalive=now

	def fileno(self):
		return self.socket.fileno()

	def loop(self,timeout):
		while not self.eof and self.socket is not None:
			self.loop_iter(timeout)

	def loop_iter(self,timeout):
		import select
		id,od,ed=select.select([self.socket],[],[self.socket],timeout)
		if self.socket in id or self.socket in ed:
			self.debug("data on input")
			self.process()
			return 1
		else:
			self.debug("input timeout")
			self.idle()
			return 0

	def process(self):
		try:
			self.read()
		except (FatalStreamError,KeyboardInterrupt,SystemExit),e:
			self.close()
			raise
		except:
			self.print_exception()

	def read(self):
		if self.eof:
			return
		r=os.read(self.socket.fileno(),1024)
		self.data_in(r)
		if r:
			try:
				self.reader.feed(r)
			except StreamParseError:
				self.send_stream_error("xml-not-well-formed")
				raise
		else:
			self.eof=1
			self.disconnect()
		if self.eof:
			self.stream_end(None)
		
	def data_in(self,data):
		self.debug("IN: %r" % (data,))

	def data_out(self,data):
		self.debug("OUT: %r" % (data,))

	def process_node(self,node):
		ns_uri=node.ns().getContent()
		if ns_uri=="http://etherx.jabber.org/streams":
			self.process_stream_node(node)
			return

		if self.require_tls and not self.tls:
			raise StreamEncryptionRequired,"TLS encryption required and not started yet"
		
		if ns_uri==self.default_ns_uri:
			stanza=StanzaFactory(node)
			self.process_stanza(stanza)
			stanza.free()
		elif ns_uri==SASL_NS:
			self.process_sasl_node(node)
		else:
			self.debug("Unhandled node: %r" % (node.serialize(),))

	def process_stream_node(self,node):
		if node.name=="error":
			e=StreamErrorNode(node)
			self.process_stream_error(e)
			e.free()
			return
		elif node.name=="features":
			self.debug("Got stream features")
			self.features=node.copyNode(1)
			self.doc_in.addChild(self.features)
			self.got_features()
			return

		if self.require_tls and not self.tls:
			raise StreamEncryptionRequired,"TLS encryption required and not started yet"
		
		self.debug("Unhandled stream node: %r" % (node.serialize(),))
	
	def process_stream_error(self,err):
		self.debug("Unhandled stream error: condition: %s %r" 
				% (err.get_condition().name,err.serialize()))

	def process_iq(self,stanza):
		id=stanza.get_id()
		fr=stanza.get_from()

		typ=stanza.get_type()
		if typ in ("result","error"):
			if fr:
				ufr=fr.as_unicode()
			else:
				ufr=None
			if self.iq_response_handlers.has_key((id,ufr)):
				key=(id,ufr)
			elif ( (fr==self.peer or fr==self.me) 
					and self.iq_response_handlers.has_key((id,None))):
				key=(id,None)
			else:
				return 0
			res_handler,err_handler=self.iq_response_handlers[key]
			if stanza.get_type()=="result":
				res_handler(stanza)
			else:
				err_handler(stanza)
			del self.iq_response_handlers[key]
			return 1

		q=stanza.get_query()
		if not q:
			r=stanza.make_error_response("bad-request")
			self.send(r)
			return 1
		el=q.name
		ns=q.ns().getContent()

		if typ=="get" and self.iq_get_handlers.has_key((el,ns)):
			self.iq_get_handlers[(el,ns)](stanza)
			return 1
		elif typ=="set" and self.iq_set_handlers.has_key((el,ns)):
			self.iq_set_handlers[(el,ns)](stanza)
			return 1
		else:
			r=stanza.make_error_response("feature-not-implemented")
			self.send(r)
			return 1

	def __try_handlers(self,handler_list,typ,stanza):
		namespaces=[]
		if stanza.node.children:
			for c in stanza.node.children:
				try:
					ns=c.ns()
				except libxml2.treeError:
					continue
				ns_uri=ns.getContent()
				if ns_uri not in namespaces:
					namespaces.append(ns_uri)
		for prio,t,ns,handler in handler_list:
			if t!=typ:
				continue
			if ns is not None and ns not in namespaces:
				continue
			if handler(stanza):
				return 1
		return 0

	def process_message(self,stanza):
		if not self.initiator and not self.peer_authenticated:
			self.debug("Ignoring message - peer not authenticated yet")
			return 1	
		
		typ=stanza.get_type()
		if self.__try_handlers(self.message_handlers,typ,stanza):
			return 1
		if typ!="error":
			return self.__try_handlers(self.message_handlers,"normal",stanza)
		return 0
		
	def process_presence(self,stanza):
		if not self.initiator and not self.peer_authenticated:
			self.debug("Ignoring presence - peer not authenticated yet")
			return 1	
		
		typ=stanza.get_type()
		if not typ:
			typ="available"
		return self.__try_handlers(self.presence_handlers,typ,stanza)

	def route_stanza(self,stanza):
		r=stanza.make_error_response("recipient-unavailable")
		self.send(r)
		return 1
		
	def process_stanza(self,stanza):
		self.fix_in_stanza(stanza)
		to=stanza.get_to()

		if to and to!=self.me and to!=self.me.bare():
			return self.route_stanza(stanza)

		if stanza.stanza_type=="iq":
			if self.process_iq(stanza):
				return
		elif stanza.stanza_type=="message":
			if self.process_message(stanza):
				return
		elif stanza.stanza_type=="presence":
			if self.process_presence(stanza):
				return
		self.debug("Unhandled %r stanza: %r" % (stanza.stanza_type,stanza.serialize()))

	def post_connect(self,node):
		pass
		
	def post_auth(self):
		pass
		
	def post_disconnect(self):
		pass

	def check_to(self,to):
		if to!=self.me:
			return None
		return to

	def fix_in_stanza(self,stanza):
		pass
		
	def fix_out_stanza(self,stanza):
		pass
		
	def set_response_handlers(self,iq,res_handler,err_handler,timeout_handler=None,timeout=300):
		self.fix_out_stanza(iq)
		to=iq.get_to()
		if to:
			to=to.as_unicode()
		if timeout_handler:
			self.iq_response_handlers[(iq.get_id(),to),timeout,timeout_handler]=(
								res_handler,err_handler)
		else:
			self.iq_response_handlers[(iq.get_id(),to),timeout]=(
								res_handler,err_handler)

	def set_iq_get_handler(self,element,namespace,handler):
		self.iq_get_handlers[(element,namespace)]=handler

	def unset_iq_get_handler(self,element,namespace):
		if self.iq_get_handlers.has_key((element,namespace)):
			del self.iq_get_handlers[(element,namespace)]

	def set_iq_set_handler(self,element,namespace,handler):
		self.iq_set_handlers[(element,namespace)]=handler

	def unset_iq_set_handler(self,element,namespace):
		if self.iq_set_handlers.has_key((element,namespace)):
			del self.iq_set_handlers[(element,namespace)]

	def __add_handler(self,handler_list,typ,namespace,priority,handler):
		if priority<0 or priority>100:
			raise StreamError,"Bad handler priority (must be in 0:100)"
		handler_list.append((priority,typ,namespace,handler))
		handler_list.sort()

	def set_message_handler(self,type,handler,namespace=None,priority=100):
		if not type:
			type=="normal"
		self.__add_handler(self.message_handlers,type,namespace,priority,handler)

	def set_presence_handler(self,type,handler,namespace=None,priority=100):
		if not type:
			type="available"
		self.__add_handler(self.presence_handlers,type,namespace,priority,handler)

	def generate_id(self):
		return "%i-%i-%s" % (os.getpid(),time.time(),str(random.random())[2:])

	def debug(self,str):
		print >>sys.stderr,"DEBUG:",str

	def print_exception(self):
		for s in traceback.format_exception(sys.exc_type,sys.exc_value,sys.exc_traceback):
			if s[-1]=='\n':
				s=s[:-1]
			self.debug(s)

	def got_features(self):
		ctxt = self.doc_in.xpathNewContext()
		ctxt.setContextNode(self.features)
		ctxt.xpathRegisterNs("stream",STREAM_NS)
		ctxt.xpathRegisterNs("tls",TLS_NS)
		ctxt.xpathRegisterNs("sasl",SASL_NS)
		try:
			tls_n=ctxt.xpathEval("tls:starttls")
			tls_required_n=ctxt.xpathEval("tls:starttls/tls:required")
			sasl_mechanisms_n=ctxt.xpathEval("sasl:mechanisms/sasl:mechanism")
		finally:
			ctxt.xpathFreeContext()
			
		if tls_required_n and not self.enable_tls:
			raise FatalStreamError,"StartTLS support disabled, but required by peer"
		if self.require_tls and not tls_n:
			raise FatalStreamError,"StartTLS required, but not supported by peer"
		if self.enable_tls and tls_n:
			self.debug("StartTLS negotiated")
			raise FatalStreamError,"StartTLS negotiated, but not implemented yet"
		self.debug("StartTLS not negotiated")
		if sasl_mechanisms_n:
			self.debug("SASL support found")
			self.peer_sasl_mechanisms=[]
			for n in sasl_mechanisms_n:
				self.peer_sasl_mechanisms.append(n.getContent())

	def connected(self):
		if self.doc_in and self.doc_out and not self.eof:
			return 1
		else:
			return 0

	def process_sasl_node(self,node):
		if self.initiator:
			if not self.authenticator:
				self.debug("Unexpected SASL response: %r" % (node.serialize()))
				return 0
			if node.name=="challenge":
				return self.process_sasl_challenge(node.getContent())
			if node.name=="success":
				return self.process_sasl_success(node.getContent())
			if node.name=="failure":
				return self.process_sasl_failure(node)
			self.debug("Unexpected SASL node: %r" % (node.serialize()))
			return 0
		else:
			if node.name=="auth":
				mechanism=node.prop("mechanism")
				return self.process_sasl_auth(mechanism,node.getContent())
			if node.name=="response":
				return self.process_sasl_response(node.getContent())
			if node.name=="abort":
				return self.process_sasl_abort()
			self.debug("Unexpected SASL node: %r" % (node.serialize()))
			return 0

	def process_sasl_auth(self,mechanism,content):
		if self.authenticator:
			self.debug("Authentication already started")
			return 0
			
		self.auth_method_used="sasl:"+mechanism
		self.authenticator=sasl.ServerAuthenticator(mechanism,self)
		self.authenticator.debug=self.debug
		
		r=self.authenticator.start(base64.decodestring(content))
	
		if isinstance(r,sasl.Success):
			el_name="success"
			content=r.base64()
		elif isinstance(r,sasl.Challenge):
			el_name="challenge"
			content=r.base64()
		else:
			el_name="failure"
			content=None
	
		root=self.doc_out.getRootElement()
		node=root.newChild(None,el_name,None)
		ns=node.newNs(SASL_NS,None)
		node.setNs(ns)
		if content:
			node.setContent(content)
		if isinstance(r,sasl.Failure):
			node.newChild(ns,r.reason,None)
		
		self.write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()

		if isinstance(r,sasl.Success):
			self.peer=JID(r.authzid)
			self.peer_authenticated=1
			self.post_auth()
			
		if isinstance(r,sasl.Failure):
			raise SASLAuthenticationFailed,"SASL authentication failed"

		return 1
		
	def process_sasl_challenge(self,content):
		if not self.authenticator:
			self.debug("Unexpected SASL challenge")
			return 0
		
		r=self.authenticator.challenge(base64.decodestring(content))
		if isinstance(r,sasl.Response):
			el_name="response"
			content=r.base64()
		else:
			el_name="abort"
			content=None
	
		root=self.doc_out.getRootElement()
		node=root.newChild(None,el_name,None)
		ns=node.newNs(SASL_NS,None)
		node.setNs(ns)
		if content:
			node.setContent(content)
		
		self.write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()

		if isinstance(r,sasl.Failure):
			raise SASLAuthenticationFailed,"SASL authentication failed"

		return 1
	
	def process_sasl_response(self,content):
		if not self.authenticator:
			self.debug("Unexpected SASL response")
			return 0
		
		r=self.authenticator.response(base64.decodestring(content))
		if isinstance(r,sasl.Success):
			el_name="success"
			content=r.base64()
		elif isinstance(r,sasl.Challenge):
			el_name="challenge"
			content=r.base64()
		else:
			el_name="failure"
			content=None
	
		root=self.doc_out.getRootElement()
		node=root.newChild(None,el_name,None)
		ns=node.newNs(SASL_NS,None)
		node.setNs(ns)
		if content:
			node.setContent(content)
		if isinstance(r,sasl.Failure):
			node.newChild(ns,r.reason,None)
		
		self.write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()
		
		if isinstance(r,sasl.Success):
			self.peer=JID(r.authzid)
			self.peer_authenticated=1
			self.post_auth()

		if isinstance(r,sasl.Failure):
			raise SASLAuthenticationFailed,"SASL authentication failed"

		return 1

	def process_sasl_success(self,content):
		if not self.authenticator:
			self.debug("Unexpected SASL response")
			return 0
			
		r=self.authenticator.finish(base64.decodestring(content))
		if isinstance(r,sasl.Success):
			el_name="success"
			self.debug("SASL authentication succeeded")
			self.me=JID(r.authzid)
			self.authenticated=1
			self.post_auth()
		else:
			self.debug("SASL authentication failed")
			raise SASLAuthenticationFailed,"Additional success data procesing failed"
		return 1

	def process_sasl_failure(self,node):
		if not self.authenticator:
			self.debug("Unexpected SASL response")
			return 0

		self.debug("SASL authentication failed: %r" % (node.serialize(),))
		raise SASLAuthenticationFailed,"SASL authentication failed"

	def process_sasl_abort(self):
		if not self.authenticator:
			self.debug("Unexpected SASL response")
			return 0

		self.authenticator=None
		self.debug("SASL authentication aborted")
		return 1

	def sasl_authenticate(self,username,authzid,mechanism=None):
		if not self.initiator:
			raise SASLAuthenticationError,"Only initiating entity start SASL authentication"
		while not self.features:
			self.debug("Waiting for features")
			self.read()
		if not self.peer_sasl_mechanisms:
			raise SASLNotAvailable,"Peer doesn't support SASL"

		if not mechanism:
			mechanism=None
			for m in self.sasl_mechanisms:
				if m in self.peer_sasl_mechanisms:
					mechanism=m
					break
			if not mechanism:
				raise SASLMechanismNotAvailable,"Peer doesn't support any of our SASL mechanisms"
			self.debug("Our mechanism: %r" % (mechanism,))
		else:
			if mechanism not in self.peer_sasl_mechanisms:
				raise SASLMechanismNotAvailable,"%s is not available" % (mechanism,)

		self.auth_method_used="sasl:"+mechanism
				
		self.authenticator=sasl.ClientAuthenticator(mechanism,self)
		self.authenticator.debug=self.debug
	
		initial_response=self.authenticator.start(username,authzid)
		if not isinstance(initial_response,sasl.Response):
			raise SASLAuthenticationFailed,"SASL initiation failed"
	
		root=self.doc_out.getRootElement()
		node=root.newChild(None,"auth",None)
		ns=node.newNs(SASL_NS,None)
		node.setNs(ns)
		node.setProp("mechanism",mechanism)
		if initial_response.data:
			node.setContent(initial_response.base64())
		
		self.write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()
