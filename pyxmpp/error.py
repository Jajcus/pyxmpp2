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

from utils import from_utf8,to_utf8
from stanza import common_doc,common_root

stream_errors_conditions={
			("host-gone","address"):1,
			("host-unknown","address"):1,
			("internal-server-error","server"):1,
			("invalid-id","format"):1,
			("invalid-namespace","format"):1,
			("nonmatching-hosts","address"):1,
			("not-authorized","access"):1,
			("remote-connection-failed","server"):1,
			("resource-constraint","server"):1,
			("see-other-host","redirect"):1,
			("system-shutdown","server"):1,
			("unsupported-stanza-type","format"):1,
			("xml-not-well-formed","format"):1,
	}

stanza_errors={
			("bad-request","format"):			400,
			("conflict","access"):				409,
			("feature-not-implemented","recipient"):	501,
			("forbidden","access"):				403,
			("internal-server-error","server"):		500,
			("item-not-found","address"):			404,
			("jid-malformed","address"):			400,
			("not-allowed","access"):			405,
			("recipient-unavailable","recipient"):		404,
			("registration-required","access"):		407,
			("remote-server-not-found","address"):		404,
			("remote-server-timeout","server"):		504,
			("service-unavailable","server"):		503,
	}

legacy_codes={
		400: ("bad-request","format"),
		401: ("not-allowed","access"),
		402: ("registration-required","access"),
		403: ("forbidden","access"),
		404: ("item-not-found","address"),
		405: ("not-allowed","access"),
		406: ("not-acceptable","bad-request"),
		407: ("registration-required","access"),
		408: ("remote-server-timeout","server"),
		409: ("conflict","access"),
		500: ("internal-server-error","server"),
		501: ("feature-not-implemented","recipient"),
		502: ("sevice-unavailable","server"),
		504: ("remote-server-timeout","server"),
		510: ("service-unavailable","server"),
	}

class ErrorNodeError(RuntimeError):
	pass


class ErrorNode:
	def __init__(self,node_or_class,condition=None,typ="stanza",copy=1,parent=None):
		""" 
		Contructor:
			ErrorNode(error_node[,copy=boolean]) -> ErrorNode
			ErrorNode(xml_node[,copy=boolean]) -> ErrorNode
			ErrorNode(class,cond_name[,parent=parent_node]) -> ErrorNode
			ErrorNode(class,
				(cond_name,cond_ns_uri,cond_content)
				[,parent=parent_node]) -> ErrorNode
		"""
		
		self.node=None
		self.borrowed=0
		if isinstance(node_or_class,libxml2.xmlNode):
			if condition is not None:
				raise ErrorNodeError,"Both condition and node given"
			clas=str(node_or_class)
			if copy:
				self.node=node_or_class.docCopyNode(common_doc,1)
			else:
				self.node=node_or_class
			common_doc.addChild(self.node)
			ns=node_or_class.ns()
			if ns.getContent() == "http://etherx.jabber.org/streams":
				self.type="stream"
			else:
				self.type="stanza"
			if copy:
				self.node.replaceNs(ns,None)
				self.node.removeNs(ns)
		elif condition is None:
			raise ErrorNodeError,"Condition not given"
		elif typ not in ("stream","stanza"):
			raise ErrorNodeError,"Bad error type"
		else:
			if parent:
				self.node=parent.newChild(None,"error",None)
				self.borrowed=1
			else:
				self.node=common_root.newChild(None,"error",None)
			self.node.setProp("class",node_or_class)
			cond=self.node.newChild(None,"condition",None)
			if typ=="stream":
				ns=cond.newNs("urn:ietf:params:xml:ns:xmpp-streams",None)
			else:
				ns=cond.newNs("urn:ietf:params:xml:ns:xmpp-stanzas",None)
			cond.setNs(ns)
			if isinstance(condition,libxml2.xmlNode):
				cond.addChild(condition.docCopyNode(common_doc,1))
			if type(condition) in (type([]),type(())):
				if len(condition)!=3:
					raise ErrorNodeError,"Condition tuple must have 3 elements"
				e=cond.newChild(None,condition[1],to_utf8(condition[2]))
				ns=e.newNs(condition[0],None)
				e.setNs(ns)
			else:
				if typ=="stream":
					d=stream_errors
				else:
					d=stanza_errors
				if not d.has_key( (str(condition),str(node_or_class)) ):
					raise ErrorNodeError,"Bad class/condition pair"
				cond.newChild(ns,condition,None)
		self.type=typ
		
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
		return not self.node.hasProp("class")

	def get_class(self):
		if not self.node.hasProp("class"):
			self.upgrade()
		return self.node.prop("class")

	def get_condition(self):
		common_xpath_ctxt.setContextNode(self.node)
		cond=common_xpath_ctxt.xpathEval('*[local-name()="condition"]/*')
		if not cond:
			self.upgrade()
			cond=common_xpath_ctxt.xpathEval('*[local-name()="condition"]/*')
			if cond:
				return cond[0]
			else:
				return None
		else:
			return cond[0]
		
	def upgrade(self):
		if not self.node.hasProp("code"):
			code=None
		else:
			try:
				code=int(self.node.prop("code"))
			except ValueError,KeyError:
				code=None
		
		if code and legacy_codes.has_key(code):
			cond,clas=legacy_codes[code]
		else:
			cond=None
			clas="server"
		
		if not self.node.hasProp("class"):
			self.node.setProp("class",clas)
		
		condition=self.node.xpathEval("condition")
		if condition:
			condition=condition[0]
			if condition.xpathEval("*"):
				return
		else:
			condition=self.node.newChild(None,"condition",None)
			if type=="stream":
				ns=condition.newNs("urn:ietf:params:xml:ns:xmpp-streams",None)
			else:
				ns=condition.newNs("urn:ietf:params:xml:ns:xmpp-stanzas",None)
			condition.setNs(ns)
		if cond:
			condition.newChild(condition.ns(),cond,None)
		else:
			content=self.node.getContent()
			c=condition.newChild(None,"unknow-legacy-error",content)
			ns=c.newNs("http://www.bnet.pl/~jajcus/pyxmpp/errors",None)
			c.setNs(ns)

	def downgrade(self):
		print "error.downgrade()"
		if self.node.hasProp("code"):
			print "error.downgrade(): no need to downgrade - code present"
			return
		if not self.node.hasProp("class"):
			print "error.downgrade(): cannot downgrade - class not present"
			return
		clas=self.node.prop("class")
		ctxt = common_doc.xpathNewContext()
		ctxt.setContextNode(self.node)
		ctxt.xpathRegisterNs("se","urn:ietf:params:xml:ns:xmpp-stanzas")
		ctxt.xpathRegisterNs("re","urn:ietf:params:xml:ns:xmpp-streams")
		cond=ctxt.xpathEval("se:condition")
		if not cond:
			cond=ctxt.xpathEval("re:condition")
		ctxt.xpathFreeContext()
		if not cond:
			print "error.downgrade(): cannot downgrade - condition not present"
			return
		cond=cond[0]
		child=cond.xpathEval("*")
		if not child:
			return
		child=child[0]
		if child.ns().getContent()!=cond.ns().getContent():
			return
		if stanza_errors.has_key( (str(child.name),str(clas)) ):
			self.node.setProp("code",str(stanza_errors[(str(child.name),str(clas))]))
		elif stream_errors.has_key( (str(child.name),str(clas)) ):
			self.node.setProp("code",str(stream_errors[(str(child.name),str(clas))]))

	def serialize(self):
		return self.node.serialize()
