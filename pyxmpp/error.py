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

stream_errors={
			u"host-gone":			1,
			u"host-unknown":		1,
			u"internal-server-error":	1,
			u"invalid-id":			1,
			u"invalid-namespace":		1,
			u"nonmatching-hosts":		1,
			u"not-authorized":		1,
			u"remote-connection-failed":	1,
			u"resource-constraint":		1,
			u"see-other-host":		1,
			u"system-shutdown":		1,
			u"unsupported-stanza-type":	1,
			u"unsupported-version":		1,
			u"xml-not-well-formed":		1,
	}

stanza_errors={
			u"bad-request":			("modify",400),
			u"conflict":			("cancel",409),
			u"feature-not-implemented":	("cancel",501),
			u"forbidden":			("auth",403),
			u"internal-server-error":	("wait",500),
			u"item-not-found":		("cancel",404),
			u"jid-malformed":		("modify",400),
			u"not-allowed":			("cancel",405),
			u"recipient-unavailable":	("wait",404),
			u"registration-required":	("auth",407),
			u"remote-server-not-found":	("cancel",404),
			u"remote-server-timeout":	("wait",504),
			u"resource-constraint":		("wait",503),
			u"service-unavailable":		("cancel",503),
			u"subscription-required":	("auth",None),
			u"unexpected-request":		("wait",None),
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
		502: "sevice-unavailable",
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
				
				if ns==ns1:
					raise ErrorNodeError,"Bad error namespace"
			self.ns=ns
			
			if copy:
				self.node=node_or_cond.docCopyNode(common_doc,1)
				common_doc.addChild(self.node)
			else:
				self.node=node_or_cond
				self.borrowed=1
				
			if copy:
				ns1=node_or_class.ns()
				self.node.replaceNs(ns1,None)
				self.node.removeNs(ns1)
		elif isinstance(node_or_cond,ErrorNode):
			if not copy:
				raise ErrorNodeError,"ErrorNodes may only be copied"
			self.ns=node_or_cond.ns
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
			self.ns=ns
		
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

	def get_condition(self):
		c=self.xpath_eval("ns:*",{'ns':self.ns.getContent()})
		if not c:
			self.upgrade()
			c=self.xpath_eval("ns:*",{'ns':self.ns.getContent()})
		if not c:
			return None
		return c[0]

	def add_custom_condition(self,ns,cond,content=None):
		c=self.node.newChild(None,cond,content)
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
			cond,typ=legacy_codes[code]
		else:
			cond=None
			typ="cancel"
		
		if not self.node.hasProp("type"):
			self.node.setProp("type",typ)
	
		condition=self.xpath_eval("ns:*",{'ns':self.ns})
		if condition:
			return
		elif cond is None:
			condition=self.node.newChild(None,"internal-server-error",None)
			ns=condition.newNs(self.ns,None)
			condition.setNs(ns)
			condition=self.node.newChild(None,"unknown-legacy-error",None)
			ns=condition.newNs(PYXMPP_ERROR_NS.ns,None)
			condition.setNs(ns)
		else:
			condition=self.node.newChild(None,cond,None)
			ns=condition.newNs(self.ns,None)
			condition.setNs(ns)

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
		if stanza_errors.has_key(cond) and stanza_errors[cond][1]:
			self.node.setProp("code",str(stanza_errors[cond][1]))

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

class StanzaErrorNode(ErrorNode):
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
			if not stanza_errors.has_key(node_or_cond):
				raise ErrorNodeError,"Bad error condition"
			
		ErrorNode.__init__(self,node_or_cond,STANZA_ERROR_NS,copy=copy,parent=parent)

		if type(node_or_cond) is UnicodeType:
			typ=stanza_errors[node_or_cond][0]
			self.node.setProp("type",typ)

	def get_type(self):
		if not self.node.hasProp("type"):
			self.upgrade()
		return self.node.prop("type")

