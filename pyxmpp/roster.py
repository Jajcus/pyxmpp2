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

import re
from types import StringType,UnicodeType
from stanza import common_doc,common_root
from iq import Iq
from jid import JID

from utils import to_utf8,from_utf8

class RosterError(StandardError):
	pass

class RosterItem:
	def __init__(self,roster,node):
		self.roster=roster
		self.node=node
	def name(self):
		return unicode(self.node.prop("name"),"utf-8")
	def jid(self):
		return JID(self.node.prop("jid"))
	def subscription(self):
		return unicode(self.node.prop("subscription"),"utf-8")
	def groups(self):
		ctxt=common_doc.xpathNewContext()
		ctxt.setContextNode(self.node)
		ctxt.xpathRegisterNs("r","jabber:iq:roster")
		l=self.xpath_ctxt.xpathEval("r:group")
		if not l:
			return []
		ret=[]
		for g in l:
			gname=g.getContent()
			if gname:
				ret.append(gname)
		return ret
		ctxt.xpathFreeContext()

class Roster:
	def __init__(self,node=None):
		self.node=None
		self.xpath_ctxt=None
		if node is None:
			self.node=common_root.newChild(None,"query",None)
			self.ns=self.node.newNs("jabber:iq:roster",None)
			self.node.setNs(self.ns)
		else:
			ns=node.ns()
			if ns.getContent() != "jabber:iq:roster":
				raise RosterError,"Bad roster namespace"
			self.node=node.docCopyNode(common_doc,1)
			common_root.addChild(self.node)
			self.ns=self.node.ns()
		self.xpath_ctxt=common_doc.xpathNewContext()
		self.xpath_ctxt.setContextNode(self.node)
		self.xpath_ctxt.xpathRegisterNs("r","jabber:iq:roster")
	
	def __del__(self):
		if self.node:
			self.node.unlinkNode()
			self.node.freeNode()
			self.node=None
		if self.xpath_ctxt:
			self.xpath_ctxt.xpathFreeContext()
			self.xpath_ctxt=None

	def items(self):
		l=self.xpath_ctxt.xpathEval("r:item")
		ret=[]
		for i in l:
			ret.append(RosterItem(self,i))
		return ret
	
	def groups(self):
		l=self.xpath_ctxt.xpathEval("r:item/r:group")
		if not l:
			return []
		ret=[]
		for g in l:
			gname=g.getContent()
			if gname:
				ret.append(gname)
		return ret
		
	def items_by_name(self,name):
		if not name:
			raise ValueError,"name is None"
		name=to_utf8(name)
		if '"' not in name:
			expr='r:item[@name="%s"]' % name
		elif "'" not in name:
			expr="r:item[@name='%s']" % name
		else:
			raise RosterError,"Unsupported roster item name format"
		l=self.xpath_ctxt.xpathEval(expr)
		if not l:
			raise KeyError,name
		ret=[]
		for i in l:
			ret.append(RosterItem(self,i))
		return ret
	
	def items_by_group(self,group):
		if not group:
			raise ValueError,"group is None"
		group=to_utf8(group)
		if '"' not in group:
			expr='r:item[r:group="%s"]' % group
		elif "'" not in group:
			expr="r:item[r:group='%s']" % group
		else:
			raise RosterError,"Unsupported roster group name format"
		l=self.xpath_ctxt.xpathEval(expr)
		if not l:
			raise KeyError,group
		ret=[]
		for i in l:
			ret.append(RosterItem(self,i))
		return ret
			
	def item_by_jid(self,jid):
		if not jid:
			raise ValueError,"jid is None"
		jid=jid.as_string()
		if '"' not in jid:
			expr='r:item[@name="%s"]' % jid
		elif "'" not in jid:
			expr="r:item[@name='%s']" % jid
		else:
			raise RosterError,"Unsupported roster item jid format"
		l=self.xpath_ctxt.xpathEval(expr)
		if not l:
			raise KeyError,str(jid)
		return append(RosterItem(self,l[0]))
