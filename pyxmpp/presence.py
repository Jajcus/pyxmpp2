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

from utils import to_utf8,from_utf8
from stanza import Stanza,StanzaError

presence_types=("available","unavailable","subscribe","unsubscribe","subscribed",
		"unsubscribed","invisible","error")

accept_responses={
		"subscribe": "subscribed",
		"subscribed": "subscribe",
		"unsubscribe": "unsubscribed",
		"unsubscribed": "unsubscribe",
		}

deny_responses={
		"subscribe": "unsubscribed",
		"subscribed": "unsubscribe",
		"unsubscribe": "subscribed",
		"unsubscribed": "subscribe",
		}

class Presence(Stanza):
	stanza_type="presence"
	def __init__(self,node=None,**kw):
		self.node=None
		if isinstance(node,Presence):
			pass
		elif isinstance(node,Stanza):
			raise TypeError,"Couldn't make Presence from other Stanza"
		elif isinstance(node,libxml2.xmlNode):
			pass
		elif node is not None:
			raise TypeError,"Couldn't make Presence from %r" % (type(node),)
	
		if kw.has_key("type") and kw["type"] and kw["type"] not in presence_types:
			raise StanzaError,"Invalid presence type: %r" % (type,)

		if kw.get("type")=="available":
			kw["type"]=None

		if kw.has_key("show"):
			show=kw["show"]
			del kw["show"]
		else:
			show=None
		if kw.has_key("status"):
			status=kw["status"]
			del kw["status"]
		else:
			status=None
		if kw.has_key("priority"):
			priority=kw["priority"]
			del kw["priority"]
		else:
			priority=None
	
		if node is None:
			node="presence"
		apply(Stanza.__init__,[self,node],kw)
		if show:
			self.node.newTextChild(None,"show",to_utf8(show))
		if status:
			self.node.newTextChild(None,"status",to_utf8(status))
		if priority and priority!=0:
			self.node.newTextChild(None,"priority",to_utf8(str(priority)))

	def copy(self):
		return Presence(self)

	def set_status(self,status):
		n=self.xpath_eval("status")
		if not status:
			if n:
				n[0].unlinkNode()
				n[0].freeNode()
			else:
				return
		if n:
			n[0].setContent(to_utf8(status))
		else:
			self.node.newTextChild(None,"status",to_utf8(status))

	def get_status(self):
		n=self.xpath_eval("status")
		if n:
			return from_utf8(n[0].getContent())
		else:
			return None
	
	def get_show(self):
		n=self.xpath_eval("show")
		if n:
			return from_utf8(n[0].getContent())
		else:
			return None

	def set_show(self,show):
		n=self.xpath_eval("show")
		if not show:
			if n:
				n[0].unlinkNode()
				n[0].freeNode()
			else:
				return
		if n:
			n[0].setContent(to_utf8(show))
		else:
			self.node.newTextChild(None,"show",to_utf8(show))

	def get_priority(self):
		n=self.xpath_eval("priority")
		if not n:
			return 0
		try:
			prio=int(n[0].getContent())
		except ValueError:
			return 0
		return prio
	
	def set_priority(self,priority):
		n=self.xpath_eval("priority")
		if not priority:
			if n:
				n[0].unlinkNode()
				n[0].freeNode()
			else:
				return
		priority=int(priority)
		if priority<-128 or priority>127:
			raise ValueError,"Bad priority value"
		priority=str(priority)
		if n:
			n[0].setContent(priority)
		else:
			self.node.newTextChild(None,"priority",priority)
		
	def make_accept_response(self):
		if self.get_type() not in ("subscribe","subscribed","unsubscribe","unsubscribed"):
			raise StanzaError,("Results may only be generated for 'subscribe',"
				"'subscribed','unsubscribe' or 'unsubscribed' presence")
		
		pr=Presence(type=accept_responses[self.get_type()],
			fr=self.get_to(),to=self.get_from(),id=self.get_id())
		return pr

	def make_deny_response(self):
		if self.get_type() not in ("subscribe","subscribed","unsubscribe","unsubscribed"):
			raise StanzaError,("Results may only be generated for 'subscribe',"
				"'subscribed','unsubscribe' or 'unsubscribed' presence")
		
		pr=Presence(type=accept_responses[self.get_type()],
			fr=self.get_to(),to=self.get_from(),id=self.get_id())
		return pr

	def make_error_response(self,cond):
		if self.get_type() == "error":
			raise StanzaError,"Errors may not be generated in response to errors"
		
		p=Presence(type="error",fr=self.get_to(),to=self.get_from(),
			id=self.get_id(),error_cond=cond)
		
		if self.node.children:
			n=self.node.children
			while n:
				p.node.children.addPrevSibling(n.copyNode(1))
				n=n.next
		return p

