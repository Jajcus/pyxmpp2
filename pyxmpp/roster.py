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

from types import StringType,UnicodeType
from stanza import common_doc,common_root
from iq import Iq
from jid import JID

from utils import to_utf8,from_utf8

class RosterError(StandardError):
	pass

class RosterItem:
	def __init__(self,roster,node_or_jid,subscription="none"):
		self.roster=roster
		if isinstance(node_or_jid,JID):
			if roster:
				self.node=roster.node.newChild(roster.node.ns(),"item",None)
			else:
				self.node=common_root.newChild(None,"item",None)
				ns=self.node.newNs("jabber:iq:roster",None)
				self.node.setNs(ns)
			self.node.setProp("jid",node_or_jid.as_string())
			self.set_subscription(subscription)
		else:
			if roster is None:
				self.node=node_or_jid.copyNode(1)
			else:
				self.node=node_or_jid
		self.xpath_ctxt=common_doc.xpathNewContext()
		self.xpath_ctxt.setContextNode(self.node)
		self.xpath_ctxt.xpathRegisterNs("r","jabber:iq:roster")
	def __del__(self):
		if self.roster is None:
			if self.node:
				self.node.unlinkNode()
				self.node.freeNode()
				self.node=None
		if self.xpath_ctxt:
			self.xpath_ctxt.xpathFreeContext()
	def name(self):
		name=self.node.prop("name")
		if name is None:
			return None
		return unicode(name,"utf-8")
	def set_name(self,name):
		if name is None:
			if self.node.hasProp("name"):
				self.node.unsetProp("name")
			return
		self.node.setProp("name",name.encode("utf-8"))
	def ask(self):
		ask=self.node.prop("ask")
		if ask is None:
			return None
		return unicode(ask,"utf-8")
	def set_ask(self,ask):
		if ask is None:
			if self.node.hasProp("ask"):
				self.node.unsetProp("ask")
			return
		self.node.setProp("ask",ask.encode("utf-8"))
	def jid(self):
		return JID(self.node.prop("jid"))
	def set_jid(self,jid):
		self.node.setProp("jid",jid.encode("utf-8"))
	def subscription(self):
		return unicode(self.node.prop("subscription"),"utf-8")
	def set_subscription(self,subscription):
		self.node.setProp("subscription",subscription.encode("utf-8"))
	def groups(self):
		l=self.xpath_ctxt.xpathEval("r:group")
		if not l:
			return []
		ret=[]
		for g in l:
			gname=g.getContent()
			if gname:
				ret.append(gname)
		return ret
	def add_group(self,group):
		group=to_utf8(group)
		if '"' not in group:
			expr='[r:group="%s"]' % (group,)
		elif "'" not in group:
			expr="[r:group='%s']" % (group,)
		else:
			raise RosterError,"Unsupported roster group name format"
		g=self.xpath_ctxt.xpathEval(expr)
		if g:
			return
		self.node.newChild(self.node.ns(),"group",group)
	def clear_groups(self):
		groups=self.xpath_ctxt.xpathEval("r:group")
		if not groups:
			return
		for g in groups:
			g.unlinkNode()
			g.freeNode()
	def rm_group(self,group):
		if group is None:
			return
		group=to_utf8(group)
		if '"' not in group:
			expr='[r:group="%s"]' % (group,)
		elif "'" not in group:
			expr="[r:group='%s']" % (group,)
		else:
			raise RosterError,"Unsupported roster group name format"
		groups=self.xpath_ctxt.xpathEval(expr)
		if not groups:
			return
		for g in groups:
			g.unlinkNode()
			g.freeNode()

class Roster:
	def __init__(self,node=None,server=0):
		self.server=server
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
		ret=[]
		l=self.xpath_ctxt.xpathEval("r:item/r:group")
		if l is not None:
			for g in l:
				gname=g.getContent()
				if gname and gname not in ret:
					ret.append(gname)
		l=self.xpath_ctxt.xpathEval("r:item[not(r:group)]")
		if l:
			ret.append(None)
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
			expr="r:item[not(r:group)]"
		else:
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
		if isinstance(jid,JID):
			jid=jid.as_string()
		if '"' not in jid:
			expr='r:item[@jid="%s"]' % jid
		elif "'" not in jid:
			expr="r:item[@jid='%s']" % jid
		else:
			raise RosterError,"Unsupported roster item jid format"
		l=self.xpath_ctxt.xpathEval(expr)
		if not l:
			raise KeyError,str(jid)
		return RosterItem(self,l[0])

	def add_item(self,jid,subscription="none"):
		try:
			item=self.item_by_jid(jid)
			raise RosterError,"Item already exists"
		except KeyError:
			pass
		if not self.server or subscription not in ("none","from","to","both"):
			subscription="none"
		item=RosterItem(self,jid,subscription)
		return item

	def rm_item(self,jid):
		item=self.item_by_jid(jid)
		item.node.unlinkNode()
		item.node.freeNode()
		item.node=None
		return RosterItem(None,jid,"remove")

	def update(self,query):
		ctxt=common_doc.xpathNewContext()
		ctxt.setContextNode(query)
		ctxt.xpathRegisterNs("r","jabber:iq:roster")
		item=ctxt.xpathEval("r:item")
		ctxt.xpathFreeContext()
		if not item:
			raise RosterError,"Not item to update"
		item=item[0]
		item=RosterItem(None,item)
		jid=item.jid()
		subscription=item.subscription()
		try:
			local_item=self.item_by_jid(jid)
		except KeyError:
			if subscription=="remove":
				return None
			if self.server or subscription not in ("none","from","to","both"):
				subscription="none"
			local_item=RosterItem(self,jid,subscription)
		if subscription=="remove":
			local_item.node.unlinkNode()
			local_item.node.freeNode()
			local_item.node=None
			return RosterItem(None,jid,"remove")
		local_item.set_name(item.name())
		if item.groups() != local_item.groups():
			local_item.clear_groups()
			for g in item.groups():
				local_item.add_group(g)
		if not self.server:
			local_item.set_ask(item.ask())
		return local_item
