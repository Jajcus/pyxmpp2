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
from stanza import Stanza,StanzaError
from utils import to_utf8,from_utf8

message_types=("normal","chat","headline","error")

class Message(Stanza):
	stanza_type="message"
	def __init__(self,node=None,**kw):
		self.node=None
		if isinstance(node,Message):
			pass
		elif isinstance(node,Stanza):
			raise TypeError,"Couldn't make Message from other Stanza"
		elif isinstance(node,libxml2.xmlNode):
			pass
		elif node is not None:
			raise TypeError,"Couldn't make Message from %r" % (type(node),)
	
		if kw.has_key("type") and kw["type"] and kw["type"] not in message_types:
			raise StanzaError,"Invalid message type: %r" % (kw["type"],)

		if kw.has_key("body"):
			body=kw["body"]
			del kw["body"]
		else:
			body=None
		if kw.has_key("subject"):
			subject=kw["subject"]
			del kw["subject"]
		else:
			subject=None
	
		if node is None:
			node="message"
		apply(Stanza.__init__,[self,node],kw)
		if subject:
			self.node.newChild(None,"subject",to_utf8(subject))
		if body:
			self.node.newChild(None,"body",to_utf8(body))

	def get_subject(self):
		n=self.xpath_eval("subject")
		if n:
			return from_utf8(n[0].getContent())
		else:
			return None
	
	def copy(self):
		return Message(self)

	def get_body(self):
		n=self.xpath_eval("body")
		if n:
			return from_utf8(n[0].getContent())
		else:
			return None

	def make_error_response(self,cond):
		if self.get_type() == "error":
			raise StanzaError,"Errors may not be generated in response to errors"
		
		m=Message(type="error",fr=self.get_to(),to=self.get_from(),
			id=self.get_id(),error_cond=cond)

		if self.node.children:
			for n in list(self.node.children):
				n=n.copyNode(1)
				m.node.children.addPrevSibling(n)
		return m
	
