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
import threading


from types import StringType,UnicodeType

from expdict import ExpiringDictionary
from utils import from_utf8,to_utf8
from stanza import Stanza,common_doc,StanzaError
from error import StreamErrorNode
from iq import Iq
from presence import Presence
from message import Message
from jid import JID
import sasl
import resolver

try:
	from M2Crypto import SSL
	from M2Crypto.SSL import SSLError
	import M2Crypto.SSL.cb
	tls_available=1
except ImportError:
	tls_available=0
	class SSLError(Exception):
		"dummy"
		pass

STREAM_NS="http://etherx.jabber.org/streams"
TLS_NS="urn:ietf:params:xml:ns:xmpp-tls"
SASL_NS="urn:ietf:params:xml:ns:xmpp-sasl"
BIND_NS="urn:ietf:params:xml:ns:xmpp-bind"

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

class TLSNegotiationFailed(FatalStreamError):
	pass

class TLSError(FatalStreamError):
	pass

class TLSSettings:
	def __init__(self,require=0,verify_peer=1,cert_file=None,key_file=None,
			cacert_file=None,verify_callback=None,
			ctx=None):
		self.require=require
		self.ctx=ctx
		self.verify_peer=verify_peer
		self.cert_file=cert_file
		self.cacert_file=cacert_file
		self.key_file=key_file
		self.verify_callback=verify_callback
		
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
					tls_settings=None,keepalive=0):
		self.default_ns_uri=default_ns
		self.extra_ns_uris=extra_ns
		self.sasl_mechanisms=sasl_mechanisms
		self.tls_settings=tls_settings
		self.keepalive=keepalive
		self.lock=threading.RLock()
		self.reader_lock=threading.Lock()
		self.process_all_stanzas=0
		self._reset()

	def _reset(self):
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
		self.tls=None
		self.tls_requested=0
		self.authenticator=None
		self.authenticated=0
		self.peer_authenticated=0
		self.auth_method_used=None
		self.version=None
		self.last_keepalive=0

	def __del__(self):
		self.close()

	def _connect_socket(self,sock,to=None):
		self.eof=0
		self.socket=sock
		if to:
			self.peer=JID(to)
		else:
			self.peer=None
		self.initiator=1
		self._send_stream_start()
		self._make_reader()

	def connect(self,addr,port,to=None):
		self.lock.acquire()
		try:
			return self._connect(addr,port,to)
		finally:
			self.lock.release()

	def _connect(self,addr,port,service=None,to=None):
		if to is None:
			to=str(addr)
		if service is not None:
			self.state_change("resolving srv",(addr,service))
			addrs=resolver.resolve_srv(addr,service)
			if not addrs:
				addrs=[(addr,port)]
		else:
			addrs=[(addr,port)]
		msg=None
		for addr,port in addrs:
			if type(addr) in (StringType,UnicodeType):
				self.state_change("resolving",addr)
			s=None
			for res in resolver.getaddrinfo(addr,port,0,socket.SOCK_STREAM):
				family,socktype,proto,canonname,sockaddr=res
				try:
					s=socket.socket(family,socktype,proto)
					self.state_change("connecting",sockaddr)
					s.connect(sockaddr)
					self.state_change("connected",sockaddr)
				except socket.error, msg:
					self.debug("Connect to %r failed" % (sockaddr,))
					if s:
						s.close()
						s=None
					continue
				break
			if s:
				break
		if not s:
			if msg:
				raise socket.error, msg
			else:
				raise FatalStreamError,"Cannot connect"

		self.addr=addr
		self.port=port
		self._connect_socket(s,to)
		self.last_keepalive=time.time()

	def accept(self,sock,myname):
		self.lock.acquire()
		try:
			return self._accept(sock,myname)
		finally:
			self.lock.release()

	def _accept(self,sock,myname):
		self.eof=0
		self.socket,addr=sock.accept()
		self.debug("Connection from: %r" % (addr,))
		self.addr,self.port=addr
		if myname:
			self.me=JID(myname)
		else:
			self.me=None
		self.initiator=0
		self._make_reader()
		self.last_keepalive=time.time()

	def disconnect(self):
		self.lock.acquire()
		try:
			return self._disconnect()
		finally:
			self.lock.release()
		
	def _disconnect(self):
		if self.doc_out:
			self._send_stream_end()

	def _post_connect(self):
		pass

	def _post_auth(self):
		pass

	def state_change(self,state,arg):
		self.debug("State: %s: %r" % (state,arg))

	def close(self):
		self.lock.acquire()
		try:
			return self._close()
		finally:
			self.lock.release()

	def _close(self):
		self._disconnect()
		if self.doc_in:
			self.doc_in=None
		if self.features:
			self.features=None
		self.reader=None
		self.stream_id=None
		if self.socket:
			self.socket.close()
		self._reset()

	def _make_reader(self):
		self.reader=xmlextra.StreamReader(self)

	def stream_start(self,doc):
		self.doc_in=doc
		self.debug("input document: %r" % (self.doc_in.serialize(),))
	
		try:
			r=self.doc_in.getRootElement()
			if r.ns().getContent() != STREAM_NS:
				self._send_stream_error("invalid-namespace")
				raise FatalStreamError,"Invalid namespace."
		except libxml2.treeError:
			self._send_stream_error("invalid-namespace")
			raise FatalStreamError,"Couldn't get the namespace."
			

		self.version=r.prop("version")
		if self.version and self.version!="1.0":
			self._send_stream_error("unsupported-version")
			raise FatalStreamError,"Unsupported protocol version."
		
		to_from_mismatch=0
		if self.initiator:
			self.stream_id=r.prop("id")
			peer=r.prop("from")
			if peer:
				peer=JID(peer)
			if self.peer:
				if peer and peer!=self.peer:
					self.debug("peer hostname mismatch:"
						" %r != %r" % (peer,self.peer))
					to_from_mismatch=1
			else:
				self.peer=peer
		else:
			to=r.prop("to")
			if to:
				to=self.check_to(to)
				if not to:
					self._send_stream_error("host-unknown")
					raise FatalStreamError,'Bad "to"'
				self.me=JID(to)
			self._send_stream_start(self.generate_id())
			self._send_stream_features()
			self.state_change("fully connected",self.peer)
			self._post_connect()

		if not self.version:
			self.state_change("fully connected",self.peer)
			self._post_connect()

		if to_from_mismatch:
			raise HostMismatch

	def stream_end(self,doc):
		self.debug("Stream ended")
		self.eof=1
		if self.doc_out:
			self._send_stream_end()
		if self.doc_in:
			self.doc_in=None
			self.reader=None
			if self.features:
				self.features=None
		self.state_change("disconnected",self.peer)

	def stanza_start(self,doc,node):
		pass

	def stanza_end(self,doc,node):
		self._process_node(node)

	def error(self,desc):
		raise StreamParseError,desc
				
	def _send_stream_end(self):
		self.doc_out.getRootElement().addContent(" ")
		s=self.doc_out.getRootElement().serialize(encoding="UTF-8")
		end=s.rindex("<")
		try:
			self._write_raw(s[end:])
		except (IOError,SystemError,socket.error),e:
			self.debug("Sending stream closing tag failed:"+str(e))
		self.doc_out.freeDoc()
		self.doc_out=None
		if self.features:
			self.features=None
		
	def _send_stream_start(self,id=None):
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
		self._write_raw(sr[:sr.find("/>")]+">")
	
	def _send_stream_error(self,condition):
		if not self.doc_out:
			self._send_stream_start()
		e=StreamErrorNode(condition)
		e.node.setNs(self.stream_ns)
		self._write_raw(e.serialize())
		e.free()
		self._send_stream_end()

	def _restart_stream(self):
		self.reader=None
		#self.doc_out.freeDoc()
		self.doc_out=None
		#self.doc_in.freeDoc() # memleak, but the node which caused the restart 
					# will be freed after this function returns
		self.doc_in=None
		self.features=None
		if self.initiator:
			self._send_stream_start(self.stream_id)
		self._make_reader()
			
	def _get_stream_features(self):
		root=self.doc_out.getRootElement()
		features=root.newChild(root.ns(),"features",None)
		if self.sasl_mechanisms and not self.authenticated:
			ml=features.newChild(None,"mechanisms",None)
			ns=ml.newNs(SASL_NS,None)
			ml.setNs(ns)
			for m in self.sasl_mechanisms:
				if m in sasl.all_mechanisms:
					ml.newTextChild(ns,"mechanism",m)
		if self.tls_settings and not self.tls:
			tls=features.newChild(None,"starttls",None)
			ns=tls.newNs(TLS_NS,None)
			tls.setNs(ns)
			if self.tls_settiongs.require:
				tls.newChild(ns,"required",None)
		return features
		
	def _send_stream_features(self):
		self.features=self._get_stream_features()
		self._write_raw(self.features.serialize(encoding="UTF-8"))

	def _write_raw(self,str):
		self.data_out(str)
		try:
			self.socket.send(str)
		except (IOError,OSError),e: 
			raise FatalStreamError("IO Error: "+str(e))
		except SSLError,e:
			raise TLSError("TLS Error: "+str(e))
	
	def write_raw(self,str):
		self.lock.acquire()
		try:
			return self._write_raw(str)
		finally:
			self.lock.release()

	def _write_node(self,node):
		if self.eof or not self.socket or not self.doc_out:
			self.debug("Dropping stanza: %r" % (node,))
			return
		node=node.docCopyNode(self.doc_out,1)
		self.doc_out.addChild(node)
		#node.reconciliateNs(self.doc_out)
		self._write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()
		
	def send(self,stanza):
		self.lock.acquire()
		try:
			return self._send(stanza)
		finally:
			self.lock.release()
		
	def _send(self,stanza):
		if self.tls_settings and self.tls_settings.require and not self.tls:
			raise StreamEncryptionRequired,"TLS encryption required and not started yet"
			
		if not self.version:
			try:
				err=stanza.get_error()
			except StanzaError:
				err=None
			if err:
				err.downgrade()
		self.fix_out_stanza(stanza)
		self._write_node(stanza.node)

	def idle(self):
		self.lock.acquire()
		try:
			return self._idle()
		finally:
			self.lock.release()

	def _idle(self):
		self.iq_response_handlers.expire()
		if not self.socket or self.eof:
			return
		now=time.time()
		if self.keepalive and now-self.last_keepalive>=self.keepalive:
			self._write_raw(" ")
			self.last_keepalive=now

	def fileno(self):
		self.lock.acquire()
		try:
			return self.socket.fileno()
		finally:
			self.lock.release()

	def loop(self,timeout):
		self.lock.acquire()
		try:
			while not self.eof and self.socket is not None:
				self._loop_iter(timeout)
		finally:
			self.lock.release()

	def loop_iter(self,timeout):
		self.lock.acquire()
		try:
			return self._loop_iter(timeout)
		finally:
			self.lock.release()
		
	def _loop_iter(self,timeout):
		import select
		self.lock.release()
		try:
			id,od,ed=select.select([self.socket],[],[self.socket],timeout)
		finally:
			self.lock.acquire()
		if self.socket in id or self.socket in ed:
			self._process()
			return 1
		else:
			self._idle()
			return 0

	def process(self):
		self.lock.acquire()
		try:
			self._process()
		finally:
			self.lock.release()
		
	def _process(self):
		try:
			self._read()
		except SSLError,e:
			self.close()
			raise TLSError("TLS Error: "+str(e))
		except (IOError,OSError),e: 
			self.close()
			raise FatalStreamError("IO Error: "+str(e))
		except (FatalStreamError,KeyboardInterrupt,SystemExit),e:
			self.close()
			raise
		except:
			self.print_exception()

	def _read(self):
		if self.eof:
			return
		if not self.tls:
			r=os.read(self.socket.fileno(),1024)
		else:
			r=self.socket.read()
			if r is None:
				return
		self.data_in(r)
		if r:
			try:
				self.reader.feed(r)
			except StreamParseError:
				self._send_stream_error("xml-not-well-formed")
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

	def _process_node(self,node):
		ns_uri=node.ns().getContent()
		if ns_uri=="http://etherx.jabber.org/streams":
			self._process_stream_node(node)
			return
		elif ns_uri==TLS_NS:
			self._process_tls_node(node)
			return

		if self.tls_settings and self.tls_settings.require and not self.tls:
			raise StreamEncryptionRequired,"TLS encryption required and not started yet"
		
		if ns_uri==self.default_ns_uri:
			stanza=StanzaFactory(node)
			self.lock.release()
			try:
				self.process_stanza(stanza)
			finally:
				self.lock.acquire()
				stanza.free()
		elif ns_uri==SASL_NS:
			self._process_sasl_node(node)
		else:
			self.debug("Unhandled node: %r" % (node.serialize(),))

	def _process_stream_node(self,node):
		if node.name=="error":
			e=StreamErrorNode(node)
			self.lock.release()
			try:
				self.process_stream_error(e)
			finally:
				self.lock.acquire()
				e.free()
			return
		elif node.name=="features":
			self.debug("Got stream features")
			self.debug("Node: %r" % (node,))
			self.features=node.copyNode(1)
			self.doc_in.addChild(self.features)
			self._got_features()
			return

		if self.tls_settings and self.tls_settings.require and not self.tls:
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
		if stanza.get_type() not in ("error","result"):
			r=stanza.make_error_response("recipient-unavailable")
			self.send(r)
		return 1
		
	def process_stanza(self,stanza):
		self.fix_in_stanza(stanza)
		to=stanza.get_to()

		if not self.process_all_stanzas and to and to!=self.me and to!=self.me.bare():
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

	def check_to(self,to):
		if to!=self.me:
			return None
		return to

	def fix_in_stanza(self,stanza):
		pass
		
	def fix_out_stanza(self,stanza):
		pass
		
	def set_response_handlers(self,iq,res_handler,err_handler,timeout_handler=None,timeout=300):
		self.lock.acquire()
		try:
			self._set_response_handlers(iq,res_handler,err_handler,timeout_handler,timeout)
		finally:
			self.lock.release()
		
	def _set_response_handlers(self,iq,res_handler,err_handler,timeout_handler=None,timeout=300):
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
		self.lock.acquire()
		try:
			self.iq_get_handlers[(element,namespace)]=handler
		finally:
			self.lock.release()

	def unset_iq_get_handler(self,element,namespace):
		self.lock.acquire()
		try:
			if self.iq_get_handlers.has_key((element,namespace)):
				del self.iq_get_handlers[(element,namespace)]
		finally:
			self.lock.release()

	def set_iq_set_handler(self,element,namespace,handler):
		self.lock.acquire()
		try:
			self.iq_set_handlers[(element,namespace)]=handler
		finally:
			self.lock.release()

	def unset_iq_set_handler(self,element,namespace):
		self.lock.acquire()
		try:
			if self.iq_set_handlers.has_key((element,namespace)):
				del self.iq_set_handlers[(element,namespace)]
		finally:
			self.lock.release()

	def __add_handler(self,handler_list,typ,namespace,priority,handler):
		if priority<0 or priority>100:
			raise StreamError,"Bad handler priority (must be in 0:100)"
		handler_list.append((priority,typ,namespace,handler))
		handler_list.sort()

	def set_message_handler(self,type,handler,namespace=None,priority=100):
		self.lock.acquire()
		try:
			if not type:
				type=="normal"
			self.__add_handler(self.message_handlers,type,namespace,priority,handler)
		finally:
			self.lock.release()

	def set_presence_handler(self,type,handler,namespace=None,priority=100):
		self.lock.acquire()
		try:
			if not type:
				type="available"
			self.__add_handler(self.presence_handlers,type,namespace,priority,handler)
		finally:
			self.lock.release()

	def generate_id(self):
		return "%i-%i-%s" % (os.getpid(),time.time(),str(random.random())[2:])

	def debug(self,str):
		print >>sys.stderr,"DEBUG:",str

	def print_exception(self):
		for s in traceback.format_exception(sys.exc_type,sys.exc_value,sys.exc_traceback):
			if s[-1]=='\n':
				s=s[:-1]
			self.debug(s)

	def _got_features(self):
		ctxt = self.doc_in.xpathNewContext()
		ctxt.setContextNode(self.features)
		ctxt.xpathRegisterNs("stream",STREAM_NS)
		ctxt.xpathRegisterNs("tls",TLS_NS)
		ctxt.xpathRegisterNs("sasl",SASL_NS)
		ctxt.xpathRegisterNs("bind",BIND_NS)
		try:
			tls_n=ctxt.xpathEval("tls:starttls")
			tls_required_n=ctxt.xpathEval("tls:starttls/tls:required")
			sasl_mechanisms_n=ctxt.xpathEval("sasl:mechanisms/sasl:mechanism")
			bind_n=ctxt.xpathEval("bind:bind")
		finally:
			ctxt.xpathFreeContext()
		
		if not self.tls:
			if tls_required_n and not self.tls_settings:
				raise FatalStreamError,"StartTLS support disabled, but required by peer"
			if self.tls_settings and self.tls_settings.require and not tls_n:
				raise FatalStreamError,"StartTLS required, but not supported by peer"
			if self.tls_settings and tls_n:
				self.debug("StartTLS negotiated")
				if not tls_available:
					raise FatalStreamError,("StartTLS negotiated, but not available"
							" (M2Crypto module required)")
				if self.initiator:
					self._request_tls()
			else:
				self.debug("StartTLS not negotiated")
		if sasl_mechanisms_n:
			self.debug("SASL support found")
			self.peer_sasl_mechanisms=[]
			for n in sasl_mechanisms_n:
				self.peer_sasl_mechanisms.append(n.getContent())
		if not self.tls_requested and not self.authenticated:
			self.state_change("fully connected",self.peer)
			self._post_connect()
			
		if self.authenticated:
			if bind_n:
				self.bind(self.jid.resource)
			else:
				self.state_change("authorized",self.jid)

	def bind(self,resource):
		iq=Iq(type="set")
		q=iq.new_query(BIND_NS,"bind")
		if resource:
			q.newTextChild(q.ns(),"resource",to_utf8(resource))
		self.state_change("binding",resource)
		self.send(iq)
		self.set_response_handlers(iq,self._bind_success,self._bind_error)
		iq.free()

	def _bind_success(self,stanza):
		jid_n=stanza.xpath_eval("bind:bind/bind:jid",{"bind":BIND_NS})
		if jid_n:
			self.me=JID(jid_n[0].getContent())
		self.state_change("authorized",self.me)
	
	def _bind_error(self,stanza):
		raise FatalStreamError,"Resource binding failed"

	def connected(self):
		if self.doc_in and self.doc_out and not self.eof:
			return 1
		else:
			return 0

	def _process_sasl_node(self,node):
		if self.initiator:
			if not self.authenticator:
				self.debug("Unexpected SASL response: %r" % (node.serialize()))
				return 0
			if node.name=="challenge":
				return self._process_sasl_challenge(node.getContent())
			if node.name=="success":
				return self._process_sasl_success(node.getContent())
			if node.name=="failure":
				return self._process_sasl_failure(node)
			self.debug("Unexpected SASL node: %r" % (node.serialize()))
			return 0
		else:
			if node.name=="auth":
				mechanism=node.prop("mechanism")
				return self._process_sasl_auth(mechanism,node.getContent())
			if node.name=="response":
				return self._process_sasl_response(node.getContent())
			if node.name=="abort":
				return self._process_sasl_abort()
			self.debug("Unexpected SASL node: %r" % (node.serialize()))
			return 0

	def _process_sasl_auth(self,mechanism,content):
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
		
		self._write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()

		if isinstance(r,sasl.Success):
			if r.authzid:
				self.peer=JID(r.authzid)
			else:
				self.peer=JID(r.username,self.me.domain)
			self.peer_authenticated=1
			self.state_change("authenticated",self.peer)
			self._post_auth()
			
		if isinstance(r,sasl.Failure):
			raise SASLAuthenticationFailed,"SASL authentication failed"

		return 1
		
	def _process_sasl_challenge(self,content):
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
		
		self._write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()

		if isinstance(r,sasl.Failure):
			raise SASLAuthenticationFailed,"SASL authentication failed"

		return 1
	
	def _process_sasl_response(self,content):
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
		
		self._write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()
		
		if isinstance(r,sasl.Success):
			authzid=r.authzid
			if authzid:
				self.peer=JID(r.authzid)
			else:
				self.peer=JID(r.username,self.me.domain)
			self.peer_authenticated=1
			self._restart_stream()
			self.state_change("authenticated",self.peer)
			self._post_auth()

		if isinstance(r,sasl.Failure):
			raise SASLAuthenticationFailed,"SASL authentication failed"

		return 1

	def _process_sasl_success(self,content):
		if not self.authenticator:
			self.debug("Unexpected SASL response")
			return 0
			
		r=self.authenticator.finish(base64.decodestring(content))
		if isinstance(r,sasl.Success):
			el_name="success"
			self.debug("SASL authentication succeeded")
			if r.authzid:
				self.me=JID(r.authzid)
			else:
				self.me=self.jid
			self.authenticated=1
			self._restart_stream()
			self.state_change("authenticated",self.me)
			self._post_auth()
		else:
			self.debug("SASL authentication failed")
			raise SASLAuthenticationFailed,"Additional success data procesing failed"
		return 1

	def _process_sasl_failure(self,node):
		if not self.authenticator:
			self.debug("Unexpected SASL response")
			return 0

		self.debug("SASL authentication failed: %r" % (node.serialize(),))
		raise SASLAuthenticationFailed,"SASL authentication failed"

	def _process_sasl_abort(self):
		if not self.authenticator:
			self.debug("Unexpected SASL response")
			return 0

		self.authenticator=None
		self.debug("SASL authentication aborted")
		return 1

	def _sasl_authenticate(self,username,authzid,mechanism=None):
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
		
		self._write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()

	def _request_tls(self):
		self.tls_requested=1
		self.features=None
		root=self.doc_out.getRootElement()
		node=root.newChild(None,"starttls",None)
		ns=node.newNs(TLS_NS,None)
		node.setNs(ns)
		self._write_raw(node.serialize(encoding="UTF-8"))
		node.unlinkNode()
		node.freeNode()

	def _process_tls_node(self,node):
		if not self.tls_settings or not tls_available:
			self.debug("Unexpected TLS node: %r" % (node.serialize()))
			return 0
		if self.initiator:
			if node.name=="failure":
				raise TLSHanshakeFailed,"Peer failed to initialize TLS connection"
			elif node.name!="proceed" or not self.tls_requested:
				self.debug("Unexpected TLS node: %r" % (node.serialize()))
				return 0
			try:
				self.tls_requested=0
				self._make_tls_connection()
				self.socket=self.tls
			except SSLError,e:
				self.tls=0
				raise TLSError("TLS Error: "+str(e))
			self.debug("Restarting XMPP stream")
			self._restart_stream()
			return 0
		else:
			raise FatalStreamError,"TLS not implemented for the receiving side yet"

	def _make_tls_connection(self,mode="connect"):
		if not tls_available or not self.tls_settings:
			raise TLSError,"TLS is not available"
			
		self.state_change("tls connecting",self.peer)
		self.debug("Creating TLS context")
		if self.tls_settings.ctx:
			ctx=self.tls_settings.ctx
		else:
			ctx=SSL.Context('tlsv1')

		ctx._pyxmpp_stream=self
			
		if self.tls_settings.verify_peer:
			ctx.set_verify(SSL.verify_peer,10,cert_verify_callback)
		else:
			ctx.set_verify(SSL.verify_none,10)
			
		if self.tls_settings.cert_file:
			ctx.use_certificate_chain_file(self.tls_settings.cert_file)
			if key_file:
				ctx.use_PrivateKey_file(self.tls_settings.key_file)
			else:
				ctx.use_PrivateKey_file(self.tls_settings.cert_file)
			ctx.check_private_key()
		if self.tls_settings.cacert_file:
			ctx.load_verify_location(self.tls_settings.cacert_file)
		self.debug("Creating TLS connection")
		self.tls=SSL.Connection(ctx,self.socket)
		self.debug("Setting up TLS connection")
		self.tls.setup_ssl()
		self.debug("Setting TLS connect state")
		self.tls.set_connect_state()
		self.debug("Starting TLS handshake")
		self.tls.connect_ssl()
		self.state_change("tls connected",self.peer)
		self.tls.setblocking(0)
		
		# clear any exception state left by some M2Crypto broken code
		try:
			raise Exception
		except:
			pass

	def _tls_verify_callback(self,ssl_ctx_ptr, x509_ptr, errnum, depth, ok):
		try:
			self.debug("tls_verify_callback(depth=%i,ok=%i)" % (depth,ok))
			from M2Crypto.SSL.Context import map as context_map
			from M2Crypto import X509,m2
			ctx=context_map()[ssl_ctx_ptr]
			cert=X509.X509(x509_ptr)
			cb=self.tls_settings.verify_callback
			
			if ctx.get_verify_depth() < depth:
				self.debug("Certificate chain is too long (%i>%i)"
						% (depth,ctx.get_verify_depth()))
				if cb:
					ok=cb(self,ctx,cert,m2.X509_V_ERR_CERT_CHAIN_TOO_LONG,depth,0)
					if not ok:
						return 0
				else:
					return 0
					
			if ok and depth==0:
				cn=cert.get_subject().CN
				if str(cn)!=str(self.peer):
					self.debug(u"Common name does not match peer name (%s != %s)"
							% (cn,self.peer))
					if cb:
						ok=cb(self,ctx,cert,TLS_ERR_BAD_CN,depth,0)
						if not ok:
							return 0
					else:
						return 0
			ok=cb(self, ctx,cert,errnum,depth,ok)
			return ok
		except:
			self.print_exception()
			raise
							       
	def get_tls_connection(self):
		return self.tls

TLS_ERR_BAD_CN=1001
	
def cert_verify_callback(ssl_ctx_ptr, x509_ptr, errnum, depth, ok):
	from M2Crypto.SSL.Context import map as context_map
	ctx=context_map()[ssl_ctx_ptr]
	if hasattr(ctx,"_pyxmpp_stream"):
		stream=ctx._pyxmpp_stream
		if stream:
			return stream._tls_verify_callback(ssl_ctx_ptr, 
						x509_ptr, errnum, depth, ok)
	print >>sys.stderr,"Falling back to M2Crypto default verify callback"
	return M2Crypto.SSL.cb.ssl_verify_callback(ssl_ctx_ptr, 
						x509_ptr, errnum, depth, ok)
