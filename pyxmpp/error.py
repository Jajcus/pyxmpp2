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
from types import StringType,UnicodeType

from utils import from_utf8,to_utf8
from stanza import common_doc,common_root
import xmlextra

stream_errors={
			u"host-gone":
				("Hostname is no longer hosted on the server",),
			u"host-unknown":
				("Hostname requested is not known to the server",),
			u"improper-addressing":
				("Improper addressing",),
			u"internal-server-error":
				("Internal server error",),
			u"invalid-id":
				("Invalid stream ID",),
			u"invalid-namespace":
				("Invalid namespace",),
			u"nonmatching-hosts":
				("Nonmatching hosts",),
			u"not-authorized":
				("Not authorized",),
			u"remote-connection-failed":
				("Remote connection failed",),
			u"resource-constraint":
				("Remote connection failed",),
			u"see-other-host":
				("Redirection required",),
			u"system-shutdown":
				("The server is being shut down",),
			u"undefined-condition":
				("Unknown error",),
			u"unsupported-stanza-type":
				("Unsupported stanza type",),
			u"unsupported-version":
				("Unsupported protocol version",),
			u"xml-not-well-formed":
				("XML sent by client is not well formed",),
	}

stanza_errors={
			u"bad-request":
				("Bad request",
				"modify",400),
			u"conflict":
				("Named session or resource already exists",
				"cancel",409),
			u"feature-not-implemented":
				("Feature requested is not implemented",
				"cancel",501),
			u"forbidden":
				("You are forbidden to perform requested action",
				"auth",403),
			u"internal-server-error":
				("Internal server error",
				"wait",500),
			u"item-not-found":
				("Item not found"
				,"cancel",404),
			u"jid-malformed":
				("JID malformed",
				"modify",400),
			u"not-allowed":
				("Requested action is not allowed",
				"cancel",405),
			u"recipient-unavailable":
				("Recipient is not available",
				"wait",404),
			u"registration-required":
				("Registration required",
				"auth",407),
			u"remote-server-not-found":
				("Remote server not found",
				"cancel",404),
			u"remote-server-timeout":
				("Remote server timeout",
				"wait",504),
			u"resource-constraint":
				("Resource constraint",
				"wait",503),
			u"service-unavailable":
				("Service is not available",
				"cancel",503),
			u"subscription-required":
				("Subscription is required",
				"auth",None),
			u"undefined-condition":
				("Unknown error",
				"cancel",None),
			u"unexpected-request":
				("Unexpected request",
				"wait",None),
	}

legacy_codes={
		400: "bad-request",
		401: "not-allowed",
		402: "registration-required",
		403: "forbidden",
		404: "item-not-found",
		405: "not-allowed",
		406: "not-acceptable",
		407: "registration-required",
		408: "remote-server-timeout",
		409: "conflict",
		500: "internal-server-error",
		501: "feature-not-implemented",
		502: "service-unavailable",
		504: "remote-server-timeout",
		510: "service-unavailable",
	}

STANZA_ERROR_NS='urn:ietf:params:xml:ns:xmpp-stanzas'
STREAM_ERROR_NS='urn:ietf:params:xml:ns:xmpp-streams'
PYXMPP_ERROR_NS='http://www.bnet.pl/~jajcus/pyxmpp/errors'
STREAM_NS="http://etherx.jabber.org/streams"

class ErrorNodeError(RuntimeError):
	pass

class ErrorNode:
	def __init__(self,node_or_cond,ns=None,copy=1,parent=None):
		""" 
		Contructor:
			ErrorNode(error_node[,copy=boolean]) -> ErrorNode
			ErrorNode(xml_node,[,copy=boolean]) -> ErrorNode
			ErrorNode(condition,ns,[,parent=parent_node]) -> ErrorNode
		"""
		
		if type(node_or_cond) is StringType:
			node_or_cond=unicode(node_or_cond,"utf-8")
		self.node=None
		self.borrowed=0
		if isinstance(node_or_cond,libxml2.xmlNode):
			if not ns:	
				ns=None
				for c in node_or_cond.children:
					ns=c.ns().getContent()
					if ns in (STREAM_ERROR_NS,STANZA_ERROR_NS):
						break
					ns=None
				
				if ns==None:
					raise ErrorNodeError,"Bad error namespace"
			self.ns=ns
			
			if copy:
				self.node=node_or_cond.docCopyNode(common_doc,1)
				common_doc.addChild(self.node)
			else:
				self.node=node_or_cond
				self.borrowed=1
				
			if copy:
				ns1=node_or_cond.ns()
				xmlextra.replace_ns(self.node,ns1,None)
				xmlextra.remove_ns(self.node,ns1)
		elif isinstance(node_or_cond,ErrorNode):
			if not copy:
				raise ErrorNodeError,"ErrorNodes may only be copied"
			self.ns=node_or_cond.ns.getContent()
			self.node=node_or_cond.node.docCopyNode(common_doc,1)
			common_doc.addChild(self.node)
		elif ns is None:
			raise ErrorNodeError,"Condition namespace not given"
		else:
			if parent:
				self.node=parent.newChild(None,"error",None)
				self.borrowed=1
			else:
				self.node=common_root.newChild(None,"error",None)
			cond=self.node.newChild(None,to_utf8(node_or_cond),None)
			ns=cond.newNs(ns,None)
			cond.setNs(ns)
			self.ns=ns.getContent()
		
	def __del__(self):
		if self.node:
			self.free()

	def free(self):
		if not self.borrowed:
			self.node.unlinkNode()
			self.node.freeNode()
		self.node=None

	def free_borrowed(self):
		self.node=None

	def is_legacy(self):
		return not self.node.hasProp("type")

	def xpath_eval(self,expr,namespaces=None):
		if not namespaces:
			return self.node.xpathEval(expr)
		ctxt = common_doc.xpathNewContext()
		ctxt.setContextNode(self.node)
		for prefix,uri in namespaces.items():
			if uri==None:
				uri=COMMON_NS
			ctxt.xpathRegisterNs(prefix,uri)
		ret=ctxt.xpathEval(expr)
		ctxt.xpathFreeContext()
		return ret

	def get_condition(self,ns=None):
		if ns is None:
			ns=self.ns
		c=self.xpath_eval("ns:*",{'ns':ns})
		if not c:
			self.upgrade()
			c=self.xpath_eval("ns:*",{'ns':ns})
		if not c:
			return None
		if ns==self.ns and c[0].name=="text":
			if len(c)==1:
				return None
			c=c[1:]
		return c[0]

	def get_text(self):
		c=self.xpath_eval("ns:*",{'ns':self.ns})
		if not c:
			self.upgrade()
		t=self.xpath_eval("ns:text",{'ns':self.ns})
		if not t:
			return None
		return t[0].getContent()

	def add_custom_condition(self,ns,cond,content=None):
		c=self.node.newTextChild(None,cond,content)
		ns=c.newNs(ns,None)
		c.setNs(ns)
		return c
		
	def upgrade(self):
		if not self.node.hasProp("code"):
			code=None
		else:
			try:
				code=int(self.node.prop("code"))
			except ValueError,KeyError:
				code=None
		
		if code and legacy_codes.has_key(code):
			cond=legacy_codes[code]
		else:
			cond=None
		
		condition=self.xpath_eval("ns:*",{'ns':self.ns})
		if condition:
			return
		elif cond is None:
			condition=self.node.newChild(None,"undefined-condition",None)
			ns=condition.newNs(self.ns,None)
			condition.setNs(ns)
			condition=self.node.newChild(None,"unknown-legacy-error",None)
			ns=condition.newNs(PYXMPP_ERROR_NS,None)
			condition.setNs(ns)
		else:
			condition=self.node.newChild(None,cond,None)
			ns=condition.newNs(self.ns,None)
			condition.setNs(ns)
		txt=self.node.getContent()
		if txt:
			text=self.node.newTextChild(None,"text",txt)
			ns=text.newNs(self.ns,None)
			text.setNs(ns)

	def downgrade(self):
		if self.node.hasProp("code"):
			return
		if not self.node.hasProp("type"):
			return
		typ=self.node.prop("type")
		cond=self.get_condition()
		if not cond:
			return
		cond=cond.name
		if stanza_errors.has_key(cond) and stanza_errors[cond][2]:
			self.node.setProp("code",str(stanza_errors[cond][2]))

	def serialize(self):
		return self.node.serialize()

class StreamErrorNode(ErrorNode):
	def __init__(self,node_or_cond,ns=None,copy=1,parent=None):
		""" 
		Contructor:
			ErrorNode(error_node[,copy=boolean]) -> ErrorNode
			ErrorNode(xml_node,[,copy=boolean]) -> ErrorNode
			ErrorNode(condition,ns,[,parent=parent_node]) -> ErrorNode
		"""
		if type(node_or_cond) is StringType:
			node_or_cond=unicode(node_or_cond,"utf-8")
		if type(node_or_cond) is UnicodeType:
			if not stream_errors.has_key(node_or_cond):
				raise ErrorNodeError,"Bad error condition"
		ErrorNode.__init__(self,node_or_cond,STREAM_ERROR_NS,copy=copy,parent=parent)

	def get_message(self):
		cond=self.get_condition()
		if not cond:
			self.upgrade()
			cond=self.get_condition()
			if not cond:
				return None
		cond=cond.name
		if not stream_errors.has_key(cond):
			return None
		return stream_errors[cond][0]

class StanzaErrorNode(ErrorNode):
	def __init__(self,node_or_cond,typ=None,copy=1,parent=None):
		""" 
		Contructor:
			ErrorNode(error_node[,copy=boolean]) -> ErrorNode
			ErrorNode(xml_node,[,copy=boolean]) -> ErrorNode
			ErrorNode(condition,ns,[,parent=parent_node]) -> ErrorNode
		"""
		if type(node_or_cond) is StringType:
			node_or_cond=unicode(node_or_cond,"utf-8")
		if type(node_or_cond) is UnicodeType:
			if not stanza_errors.has_key(node_or_cond):
				raise ErrorNodeError,"Bad error condition"
			
		ErrorNode.__init__(self,node_or_cond,STANZA_ERROR_NS,copy=copy,parent=parent)

		if type(node_or_cond) is UnicodeType:
			if typ is None:
				typ=stanza_errors[node_or_cond][1]
			self.node.setProp("type",typ)

	def get_type(self):
		if not self.node.hasProp("type"):
			self.upgrade()
		return self.node.prop("type")

	def upgrade(self):
		ErrorNode.upgrade(self)
		if self.node.hasProp("type"):
			return
		
		cond=self.get_condition().name
		if stanza_errors.has_key(cond):
			typ=stanza_errors[cond][1]
			self.node.setProp("type",typ)

	def get_message(self):
		cond=self.get_condition()
		if not cond:
			self.upgrade()
			cond=self.get_condition()
			if not cond:
				return None
		cond=cond.name
		if not stanza_errors.has_key(cond):
			return None
		return stanza_errors[cond][0]
