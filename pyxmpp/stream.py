
import libxml2
import socket
import os
import sys
import time
import random

from utils import from_utf8,to_utf8
from stanza import Stanza,common_ns,common_doc
from error import ErrorNode
from iq import Iq
from presence import Presence
from message import Message
import sasl

STREAM_NS="http://etherx.jabber.org/streams"
TLS_NS="urn:ietf:params:xml:ns:xmpp-tls"
SASL_NS="urn:ietf:params:xml:ns:xmpp-sasl"

def StanzaFactory(node):
	if node.name=="iq":
		return Iq(node)
	if node.name=="message":
		return Message(node)
	if node.name=="presence":
		return Presence(node)
	else:
		return Stanza(node)

class StreamReader:
	def __init__(self,stream):
		self.stream=stream
		self.fd=stream.socket.fileno()
	def read(self,len):
		r=os.read(self.fd,len)
		self.stream.debug("IN: %r" % (r,))
		if r=="":
			self.stream.eof_handler()
		return r

class StreamError(RuntimeError):
	pass

class HostMismatch(StreamError):
	pass

class Stream(sasl.PasswordManager):
	def __init__(self,default_ns,extra_ns=[],sasl_mechanisms=[],enable_tls=0,require_tls=0):
		self.default_ns_uri=default_ns
		self.extra_ns_uris=extra_ns
		self.sasl_mechanisms=sasl_mechanisms
		self.enable_tls=enable_tls
		self.require_tls=require_tls
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
		self.me=None
		self.peer=None
		self.skip=0
		self.stream_id=None
		self.iq_reply_handlers={}
		self.iq_get_handlers={}
		self.iq_set_handlers={}
		self.eof=0
		self.initiator=None
		self.features=None
		self.tls=0
		self.authenticator=None

	def __del__(self):
		self.close()

	def connect_socket(self,sock,to=None):
		self.eof=0
		self.socket=sock
		self.peer=to
		self.initiator=1
		self.send_stream_start()
		self.make_reader(sock)

	def connect(self,addr,port,to=None):
		if to is None:
			to=str(addr)
		s=socket.socket()
		s.connect((addr,port))
		self.addr=addr
		self.port=port
		self.connect_socket(s,to)

	def accept(self,sock,myname):
		self.eof=0
		self.socket,addr=sock.accept()
		self.addr,self.port=addr
		self.me=myname
		self.initiator=0
		self.make_reader(self.socket)

	def disconnect(self):
		if self.doc_out:
			self.send_stream_end()

	def close(self):
		self.disconnect()
		if self.doc_in:
			self.doc_in.freeDoc()
			self.doc_in=None
		if self.features:
			self.features=None
		self.reader=None
		self.stream_id=None
		if self.socket:
			self.socket.close()
		self.reset()

	def make_reader(self,sock):
		input=libxml2.inputBuffer(StreamReader(self))
		self.reader=input.newTextReader("input stream")

	def send_stream_end(self):
		self.doc_out.getRootElement().addContent(" ")
		str=self.doc_out.getRootElement().serialize(encoding="UTF-8")
		end=str.rindex("<")
		self.write_raw(str[end:])
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
			root.setProp("to",self.peer)
		root.setProp("version","1.0")
		if id:
			root.setProp("id",id)
			self.stream_id=id
		sr=self.doc_out.serialize(encoding="UTF-8")
		self.write_raw(sr[:sr.find("/>")]+">")

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
		self.debug("OUT: %r" % (str,))
		self.socket.send(str)

	def write_node(self,node):
		node=node.docCopyNode(self.doc_out,1)
		self.doc_out.addChild(node)
		node.reconciliateNs(self.doc_out)
		self.write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()
		
	def send(self,stanza):
		if self.require_tls and not self.tls:
			raise StreamError,"TLS encryption required and not started yet"
		self.write_node(stanza.node)

	def eof_handler(self):
		self.eof=1

	def idle(self):
		pass

	def loop(self,timeout):
		import select
		while not self.eof:
			id,od,ed=select.select([self.socket],[],[self.socket],timeout)
			if self.socket in id or self.socket in ed:
				self.read()
			else:
				self.idle()

	def read(self):
		self.debug("Stream.read()")
		if not self.reader:
			raise StreamError,"No reader defined. Socket not connected?"
		if self.skip:
			self.debug("skiping to the next node")
			ret=self.reader.Next()
			self.skip=0
		else:
			self.debug("reading current node")
			ret=self.reader.Read()
			
		if ret!=1 and not self.eof:
			self.debug("reader failed")
			raise StreamError,"Read error."

		self.debug("node type: %i" % (self.reader.NodeType(),))
		if self.eof or self.reader.NodeType()==15:
			self.debug("Stream ended")
			if self.doc_out:
				self.send_stream_end()
			if self.doc_in:
				self.doc_in.freeDoc()
				self.doc_in=None
				if self.features:
					self.features=None
			self.post_disconnect()
			
		if self.reader.NodeType()!=1:
			self.skip=1
			return
		if self.doc_in:
			n=self.reader.Expand()
			self.skip=1
			node=n.docCopyNode(self.doc_in,1)
			self.doc_in.getRootElement().addChild(node)
			self.process_node(node)
			node.unlinkNode()
			node.freeNode()
			return
		self.doc_in=self.reader.CurrentDoc().copyDoc(1)
		self.debug("input document: %r" % (self.doc_in.serialize(),))
		
		r=self.doc_in.getRootElement()
		if r.ns().getContent() != STREAM_NS:
			e=ErrorNode("format","invalid-namespace","stream")
			self.send_stream_error(e)
			raise StreamError,"Read error."
		self.version=r.prop("version")
		if self.version and self.version!="1.0":
			e=ErrorNode("format","unsupported-version","stream")
			self.send_stream_error(e)
			raise StreamError,"Read error."
		
		to_from_mismatch=0
		if not self.doc_out:
			self.send_stream_start(self.generate_id())
		else:
			self.stream_id=r.prop("id")
			peer=r.prop("from")
			if self.peer:
				if peer and peer!=self.peer:
					to_from_mismatch=1
			else:
				self.peer=peer

		if not self.initiator:
			self.send_stream_features()
		self.post_connect()
		if to_from_mismatch:
			raise HostMismatch

	def process_node(self,node):
		ns_uri=node.ns().getContent()
		if ns_uri=="http://etherx.jabber.org/streams":
			self.process_stream_node(node)
			return

		if self.require_tls and not self.tls:
			raise StreamError,"TLS encryption required and not started yet"
		
		if ns_uri==self.default_ns_uri:
			stanza=StanzaFactory(node)
			self.process_stanza(stanza)
			stanza.free()
		if ns_uri==SASL_NS:
			self.process_sasl_node(node)
		else:
			self.debug("Unhandled node: %r" % (node.serialize(),))

	def process_stream_node(self,node):
		if node.name=="error":
			e=ErrorNode(node)
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
			raise StreamError,"TLS encryption required and not started yet"
		
		self.debug("Unhandled stream node: %r" % (node.serialize(),))
	
	def process_stream_error(self,err):
		self.debug("Unhandled stream error: class: %s condition: %s %r" 
				% (err.get_class(),err.get_condition().name,err.serialize()))

	def process_iq(self,stanza):
		id=stanza.get_id()
		typ=stanza.get_type()
		if typ in ("result","error"):
			if self.iq_reply_handlers.has_key(id):
				res_handler,err_handler=self.iq_reply_handlers[id]
				if stanza.get_type()=="result":
					res_handler(stanza)
				else:
					err_handler(stanza)
				del self.iq_reply_handlers[id]
				return 1
			else:
				return 0

		q=stanza.get_query()
		if not q:
			return 0
		el=q.name
		ns=q.ns().getContent()

		if typ=="get" and self.iq_get_handlers.has_key((el,ns)):
			self.iq_get_handlers[(el,ns)](stanza)
			return 1
		elif typ=="set":
			self.iq_set_handlers[(el,ns)](stanza)
			return 1
		else:
			return 0

	def process_stanza(self,stanza):
		if stanza.stanza_type=="iq":
			if self.process_iq(stanza):
				return
		self.debug("Unhandled %r stanza: %r" % (stanza.stanza_type,stanza.serialize()))

	def post_connect(self,node):
		pass
		
	def post_disconnect(self,node):
		pass
		
	def set_reply_handlers(self,iq,res_handler,err_handler):
		self.iq_reply_handlers[iq.get_id()]=(res_handler,err_handler)

	def set_iq_get_handler(self,element,namespace,handler):
		self.iq_get_handlers[(element,namespace)]=handler

	def set_iq_set_handler(self,element,namespace,handler):
		self.iq_set_handlers[(element,namespace)]=handler

	def generate_id(self):
		return "%i-%i-%s" % (os.getpid(),time.time(),str(random.random())[2:])

	def debug(self,str):
		print >>sys.stderr,"DEBUG:",str

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
			raise StreamError,"StartTLS support disabled, but required by peer"
		if self.require_tls and not tls_n:
			raise StreamError,"StartTLS required, but not supported by peer"
		if self.enable_tls and tls_n:
			self.debug("StartTLS negotiated")
			raise StreamError,"StartTLS negotiated, but not implemented yet"
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
				self.debug("Unexpected SASL reply: %r" % (node.serialize()))
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
		self.authenticator=sasl.ServerAuthenticator(mechanism,self)
		
		r=self.authenticator.start(content)
		
		if isinstance(r,sasl.Success):
			el_name="success"
			content=str(r)
		elif isinstance(r,sasl.Challenge):
			el_name="challenge"
			content=str(r)
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
		return 1
		
	def process_sasl_challenge(self,content):
		if not self.authenticator:
			self.debug("Unexpected SASL challenge")
			return 0
		
		r=self.authenticator.challenge(content)
		if isinstance(r,sasl.Response):
			el_name="response"
			content=str(r)
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
		return 1
	
	def process_sasl_response(self,content):
		if not self.authenticator:
			self.debug("Unexpected SASL response")
			return 0
		
		r=self.authenticator.response(content)
		if isinstance(r,sasl.Success):
			el_name="success"
			content=str(r)
		elif isinstance(r,sasl.Challenge):
			el_name="challenge"
			content=str(r)
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
		return 1

	def process_sasl_success(self,content):
		self.debug("SASL authentication succeeded")
		self.authenticated=1
		return 1

	def process_sasl_failure(self,node):
		self.debug("SASL authentication failed: %r" % (node.serialize(),))
		return 1

	def process_sasl_abort(self):
		self.debug("SASL authentication aborted")
		return 1

	def sasl_authorize(self,username,authzid):
		if not self.initiator:
			raise StreamError,"Only initiating entity start SASL authentication"
		while not self.features:
			self.debug("Waiting for features")
			self.read()
		if not self.peer_sasl_mechanisms:
			raise StreamError,"Peer doesn't support SASL"
		choice=None
		for m in self.sasl_mechanisms:
			if m in self.peer_sasl_mechanisms:
				choice=m
				break
		if not choice:
			raise StreamError,"Peer doesn't support any of our SASL mechanisms"
		self.debug("Our choice: %r" % (choice,))
		self.authenticator=sasl.ClientAuthenticator(choice,self)
	
		initial_response=self.authenticator.start(username,authzid)
		if not isinstance(initial_response,sasl.Response):
			raise StreamError,"SASL initiation failed"
	
		root=self.doc_out.getRootElement()
		node=root.newChild(None,"auth",None)
		ns=node.newNs(SASL_NS,None)
		node.setNs(ns)
		node.setProp("mechanism",choice)
		if str(initial_response):
			node.setContent(str(initial_response))
		
		self.write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()

