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

import sys
import re
import libxml2
from types import StringType,UnicodeType

from pyxmpp.stanza import common_doc,common_root
from pyxmpp.jid import JID

from pyxmpp.utils import to_utf8,from_utf8

class DiscoError(StandardError):
	pass

class DiscoItem:
	def __init__(self,disco,xmlnode_or_jid,node,name=None,action=None):
		self.disco=disco
		if isinstance(xmlnode_or_jid,JID):
			if disco:
				self.xmlnode=disco.xmlnode.newChild(disco.xmlnode.ns(),"item",None)
			else:
				self.xmlnode=common_root.newChild(None,"item",None)
				ns=self.xmlnode.newNs("http://jabber.org/protocol/disco#items",None)
				self.xmlnode.setNs(ns)
			self.xmlnode.setProp("jid",xmlnode_or_jid.as_string())
		else:
			if disco is None:
				self.xmlnode=node_or_jid.copyNode(1)
			else:
				self.xmlnode=node_or_jid
		self.xpath_ctxt=common_doc.xpathNewContext()
		self.xpath_ctxt.setContextNode(self.xmlnode)
		self.xpath_ctxt.xpathRegisterNs("d","http://jabber.org/protocol/disco#items")
		if name is not None:
			self.set_name(name)
		if node is not None:
			self.set_node(node)
		if action is not None:
			self.set_action(action)

	def __del__(self):
		if self.disco is None:
			if self.xmlnode:
				self.xmlnode.unlinkNode()
				self.xmlnode.freeNode()
				self.xmlnode=None
		if self.xpath_ctxt:
			self.xpath_ctxt.xpathFreeContext()
	def __str__(self):
		return self.xmlnode.serialize()

	def remove(self):
		if self.disco is None:
			return
		self.xmlnode.unlinkNode()
		oldns=self.xmlnode.ns()
		ns=self.xmlnode.newNs(oldns.getContent(),None)
		self.xmlnode.replaceNs(oldns,ns)
		common_root.addChild(self.xmlnode())
		self.disco=None
	
	def name(self):
		name=self.xmlnode.prop("name")
		if name is None:
			return None
		return unicode(name,"utf-8")
	def set_name(self,name):
		if name is None:
			if self.xmlnode.hasProp("name"):
				self.xmlnode.unsetProp("name")
			return
		self.xmlnode.setProp("name",name.encode("utf-8"))
	def node(self):
		node=self.xmlnode.prop("node")
		if node is None:
			return None
		return unicode(node,"utf-8")
	def set_node(self,node):
		if node is None:
			if self.xmlnode.hasProp("node"):
				self.xmlnode.unsetProp("node")
			return
		self.xmlnode.setProp("node",node.encode("utf-8"))
	def action(self):
		action=self.xmlnode.prop("action")
		if action is None:
			return None
		return unicode(action,"utf-8")
	def set_action(self,action):
		if action is None:
			if self.xmlnode.hasProp("action"):
				self.xmlnode.unsetProp("action")
			return
		if action not in ("remove","update"):
			raise DiscoError,"Action must be 'update' or 'remove'"
		self.xmlnode.setProp("action",action.encode("utf-8"))
	def jid(self):
		return JID(self.xmlnode.prop("jid"))
	def set_jid(self,jid):
		self.xmlnode.setProp("jid",jid.encode("utf-8"))

class DiscoIdentity:
	def __init__(self,disco,xmlnode_or_name,category,type=None,replace=0):
		self.disco=disco
		if disco and replace:
			old=disco.xpath_ctxt.xpathEval("d:identity")
			if old:
				for n in old:
					n.unlinkNode()
					n.freeNode()
		if isinstance(xmlnode_or_name,libxml2.xmlNode):
			if disco is None:
				self.xmlnode=xmlnode_or_name.copyNode(1)
			else:
				self.xmlnode=xmlnode_or_name
		else:
			if disco:
				self.xmlnode=disco.xmlnode.newChild(disco.xmlnode.ns(),"identity",None)
			else:
				self.xmlnode=common_root.newChild(None,"identity",None)
				ns=self.xmlnode.newNs("http://jabber.org/protocol/disco#info",None)
				self.xmlnode.setNs(ns)
			self.xmlnode.setProp("name",to_utf8(xmlnode_or_name))
			self.xmlnode.setProp("category",to_utf8(category))
			if type:
				self.xmlnode.setProp("type",to_utf8(type))
		self.xpath_ctxt=common_doc.xpathNewContext()
		self.xpath_ctxt.setContextNode(self.xmlnode)
		self.xpath_ctxt.xpathRegisterNs("d","http://jabber.org/protocol/disco#info")

	def __del__(self):
		if self.disco is None:
			if self.xmlnode:
				self.xmlnode.unlinkNode()
				self.xmlnode.freeNode()
				self.xmlnode=None
		if self.xpath_ctxt:
			self.xpath_ctxt.xpathFreeContext()
	def __str__(self):
		return self.xmlnode.serialize()
	
	def remove(self):
		if self.disco is None:
			return
		self.xmlnode.unlinkNode()
		oldns=self.xmlnode.ns()
		ns=self.xmlnode.newNs(oldns.getContent(),None)
		self.xmlnode.replaceNs(oldns,ns)
		common_root.addChild(self.xmlnode())
		self.disco=None

	def name(self):
		var=self.xmlnode.prop("name")
		return unicode(var,"utf-8")
	def set_name(self,name):
		self.xmlnode.setProp("name",var.encode("utf-8"))
	def category(self):
		var=self.xmlnode.prop("category")
		return unicode(var,"utf-8")
	def set_category(self,category):
		self.xmlnode.setProp("category",var.encode("utf-8"))
	def type(self):
		type=self.xmltype.prop("type")
		if type is None:
			return None
		return unicode(type,"utf-8")
	def set_type(self,type):
		if type is None:
			if self.xmltype.hasProp("type"):
				self.xmltype.unsetProp("type")
			return
		self.xmltype.setProp("type",type.encode("utf-8"))

class DiscoItems:
	def __init__(self,xmlnode_or_node=None):
		self.xmlnode=None
		self.xpath_ctxt=None
		if isinstance(xmlnode_or_node,libxml2.xmlNode):
			ns=xmlnode.ns()
			if ns.getContent() != "http://jabber.org/protocol/disco#items":
				raise RosterError,"Bad disco-items namespace"
			self.xmlnode=xmlnode.docCopyNode(common_doc,1)
			common_root.addChild(self.xmlnode)
			self.ns=self.xmlnode.ns()
		else:
			self.xmlnode=common_root.newChild(None,"query",None)
			self.ns=self.xmlnode.newNs("http://jabber.org/protocol/disco#items",None)
			self.xmlnode.setNs(self.ns)
			if xmlnode_or_node:
				slef.xmlnode.setProp("node",to_utf8(xmlnode_or_node))
		self.xpath_ctxt=common_doc.xpathNewContext()
		self.xpath_ctxt.setContextNode(self.xmlnode)
		self.xpath_ctxt.xpathRegisterNs("d","http://jabber.org/protocol/disco#items")
	
	def __del__(self):
		if self.xmlnode:
			self.xmlnode.unlinkNode()
			self.xmlnode.freeNode()
			self.xmlnode=None
		if self.xpath_ctxt:
			self.xpath_ctxt.xpathFreeContext()
			self.xpath_ctxt=None

	def identities(self):
		ret=[]
		l=self.xpath_ctxt.xpathEval("d:identity")
		if l is not None:
			for i in l:
				ret.append(DiscoIdentity(i))
		return ret

	def has_item(self,jid,node=None):
		if not jid:
			raise ValueError,"bad jid"
		if isinstance(jid,JID):
			jid=jid.as_string()
		if not node:
			node_expr=""
		elif '"' not in node:
			expr=' and @node="%s"' % (node,)
		elif "'" not in node:
			expr=" and @node='%s'" % (node,)
		else:
			raise ValueError,"Invalid node name"
		if '"' not in jid:
			expr='d:feature[@jid="%s"%s]' % (jid,node_expr)
		elif "'" not in jid:
			expr="d:feature[@jid='%s'%s]" % (jid,node_expr)
		else:
			raise ValueError,"Invalid jid name"

		l=self.xpath_ctxt.xpathEval(expr)
		if l:
			return 1
		else:
			return 0

class DiscoInfo:
	def __init__(self,xmlnode_or_node=None):
		self.xmlnode=None
		self.xpath_ctxt=None
		if isinstance(xmlnode_or_node,libxml2.xmlNode):
			ns=xmlnode.ns()
			if ns.getContent() != "http://jabber.org/protocol/disco#info":
				raise RosterError,"Bad disco-info namespace"
			self.xmlnode=xmlnode.docCopyNode(common_doc,1)
			common_root.addChild(self.xmlnode)
			self.ns=self.xmlnode.ns()
		else:
			self.xmlnode=common_root.newChild(None,"query",None)
			self.ns=self.xmlnode.newNs("http://jabber.org/protocol/disco#info",None)
			self.xmlnode.setNs(self.ns)
			if xmlnode_or_node:
				slef.xmlnode.setProp("node",to_utf8(xmlnode_or_node))

		self.xpath_ctxt=common_doc.xpathNewContext()
		self.xpath_ctxt.setContextNode(self.xmlnode)
		self.xpath_ctxt.xpathRegisterNs("d","http://jabber.org/protocol/disco#info")
	
	def __del__(self):
		if self.xmlnode:
			self.xmlnode.unlinkNode()
			self.xmlnode.freeNode()
			self.xmlnode=None
		if self.xpath_ctxt:
			self.xpath_ctxt.xpathFreeContext()
			self.xpath_ctxt=None

	def features(self):
		l=self.xpath_ctxt.xpathEval("d:feature")
		ret=[]
		for f in l:
			if f.hasProp("var"):
				ret.append(unicode(f.prop("var"),"utf-8"))
		return reta

	def has_feature(self,var):
		if not var:
			raise ValueError,"var is None"
		if '"' not in var:
			expr='d:feature[@var="%s"]' % (var,)
		elif "'" not in var:
			expr="d:feature[@var='%s']" % (var,)
		else:
			raise RosterError,"Invalid feature name"

		l=self.xpath_ctxt.xpathEval(expr)
		if l:
			return 1
		else:
			return 0

	def add_feature(self,var):
		if self.has_feature(var):
			return
		n=self.xmlnode.newChild(self.ns,"feature",None)
		n.setProp("var",var)

	def remove_feature(self,var):
		if not var:
			raise ValueError,"var is None"
		if '"' not in var:
			expr='d:feature[@var="%s"]' % (var,)
		elif "'" not in var:
			expr="d:feature[@var='%s']" % (var,)
		else:
			raise RosterError,"Invalid feature name"

		l=self.xpath_ctxt.xpathEval(expr)
		if not l:
			return

		for f in l:
			f.unlinkNode()
			f.freeNode()
	
	def identities(self):
		ret=[]
		l=self.xpath_ctxt.xpathEval("d:identity")
		if l is not None:
			for i in l:
				ret.append(DiscoIdentity(i))
		return ret

	def identity_is(self,category,type=None):
		if not category:
			raise ValueError,"bad category"
		if not type:
			type_expr=""
		elif '"' not in type:
			expr=' and @type="%s"' % (type,)
		elif "'" not in type:
			expr=" and @type='%s'" % (type,)
		else:
			raise ValueError,"Invalid type name"
		if '"' not in category:
			expr='d:feature[@category="%s"%s]' % (category,type_expr)
		elif "'" not in category:
			expr="d:feature[@category='%s'%s]" % (category,type_expr)
		else:
			raise ValueError,"Invalid category name"

		l=self.xpath_ctxt.xpathEval(expr)
		if l:
			return 1
		else:
			return 0
