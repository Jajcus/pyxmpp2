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
	
		if kw.has_key("type") and kw["type"] not in presence_types:
			raise StanzaError,"Invalid presence type: %r" % (type,)

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
	
		if node is None:
			node="presence"
		apply(Stanza.__init__,[self,node],kw)
		if show:
			self.node.newChild(None,"show",to_utf8(show))
		if status:
			self.node.newChild(None,"status",to_utf8(status))

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
