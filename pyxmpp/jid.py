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

"""jid --- Jabber ID handling"""

import re
from types import StringType,UnicodeType

from utils import to_utf8,from_utf8
from xmppstringprep import nodeprep,resourceprep

node_invalid_re=re.compile(ur"[" u'"' ur"&'/:<>@\s\x00-\x19]",re.UNICODE)
resource_invalid_re=re.compile(ur"[\s\x00-\x19]",re.UNICODE)
domain_invalid_re=re.compile(r"[^-a-zA-Z0-9]")


class JIDError(ValueError):
	"Exception raised when invalid JID is used"
	pass

class JID:
	def __init__(self,node=None,domain=None,resource=None,check=1):
		"""JID(string[,check=val]) -> JID
		JID(domain[,check=val]) -> JID
		JID(node,domain[,resource][,check=val]) -> JID
		
		Constructor for JID object.
		When check argument is given and equal 0, than JID
		is not checked for specification compliance. This
		should be used only when other arguments are known 
		to be valid."""
		if isinstance(node,JID):
			self.node=node.node
			self.domain=node.domain
			self.resource=node.resource
			return
		if node and (node.find(u"@")>=0 or node.find(u"/")>=0):
			self.from_string(node)
			return
		if domain is None and resource is None:
			self.set_domain(node)
			self.node=None
			self.resource=None
			return
		
		if check:
			self.set_node(node)
			self.set_domain(domain)
			self.set_resource(resource)
		else:
			self.node=node
			self.domain=domain
			self.resource=resource
	
	def from_string(self,s,check=1):
		return self.from_unicode(from_utf8(s),check)
	
	def from_unicode(self,s,check=1):
		s1=s.split("/",1)
		s2=s1[0].split("@",1)
		if len(s2)==2:
			if check:
				self.set_node(s2[0])
				self.set_domain(s2[1])
			else:
				self.node=s2[0]
				self.domain=s2[1]
		else:
			if check:
				self.set_domain(s2[0])
			else:
				self.domain=s2[0]
			self.node=None
		if len(s1)==2:
			if check:
				self.set_resource(s1[1])
			else:
				self.resource=s1[1]
		else:
			self.resource=None

	def set_node(self,s):
		if s: 
			s=from_utf8(s)
			s=nodeprep.prepare(s)
			if len(s)>1023:
				raise JIDError,"Node name too long"
		self.node=s
		
	def set_domain(self,s):
		if s: s=from_utf8(s)
		if s is None:
			raise JIDError,"Domain must be given"
		if domain_invalid_re.match(s):
			raise JIDError,"Invalid characters in domain"
		if len(s)>1023:
			raise JIDError,"Domain name too long"
		self.domain=s
	
	def set_resource(self,s):
		if s: 
			s=from_utf8(s)
			s=resourceprep.prepare(s)
			if len(s)>1023:
				raise JIDError,"Resource name too long"
		self.resource=s
	
	def __str__(self):
		return self.as_string()
	
	def __unicode__(self):
		return self.as_unicode()
	
	def __repr__(self):
		return "<JID: %r>" % (self.as_string())
	
	def as_utf8(self):
		"Returns UTF-8 encoded JID representation"
		return self.as_unicode().encode("utf-8")

	def as_string(self):
		"Returns UTF-8 encoded JID representation"
		return self.as_utf8()
		
	def as_unicode(self):
		"Unicode JID representation"
		if not self.node and not self.resource:
			return self.domain
		elif not self.node:
			return u"%s/%s" % (self.domain,self.resource)
		elif not self.resource:
			return u"%s@%s" % (self.node,self.domain)
		else:
			return "%s@%s/%s" % (self.node,self.domain,self.resource)
	def bare(self):
		"Returns bare JID made by removing resource from current JID"
		return JID(self.node,self.domain,check=0)

	def __eq__(self,other):
		if other is None:
			return 0
		elif type(other) in (StringType,UnicodeType):
			try:
				other=JID(other)
			except:
				return 0
		elif not isinstance(other,JID):
			raise TypeError,"Can't compare JID with %r" % (type(other),)
			
		return (self.node==other.node
			and self.domain==other.domain
			and self.resource==other.resource)
	
	def __ne__(self,other):
		return not self.__eq__(other)
