
import re

from utils import to_utf8,from_utf8

node_invalid_re=re.compile(ur"[" u'"' ur"&'/:<>@\s\x00-\x19]",re.UNICODE)
resource_invalid_re=re.compile(ur"[\s\x00-\x19]",re.UNICODE)
domain_invalid_re=re.compile(r"[^-a-zA-Z]")


class JIDError(ValueError):
	pass

class JID:
	def __init__(self,node=None,domain=None,resource=None):
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
		self.set_node(node)
		self.set_domain(domain)
		self.set_resource(resource)
	
	def from_string(self,s):
		return self.from_unicode(from_utf8(s))
	
	def from_unicode(self,s):
		s1=s.split("/",1)
		s2=s1[0].split("@",1)
		if len(s2)==2:
			self.set_node(s2[0])
			self.set_domain(s2[1])
		else:
			self.set_domain(s2[0])
		if len(s1)==2:
			self.set_resource(s1[1])

	def set_node(self,s):
		if s: s=from_utf8(s)
		if s is not None and node_invalid_re.match(s):
			raise JIDError,"Invalid characters in node"
		self.node=s
		
	def set_domain(self,s):
		if s: s=from_utf8(s)
		if s is None:
			raise JIDError,"Domain must be given"
		if domain_invalid_re.match(s):
			raise JIDError,"Invalid characters in domain"
		self.domain=s
	
	def set_resource(self,s):
		if s: s=from_utf8(s)
		if s is not None and resource_invalid_re.match(s):
			raise JIDError,"Invalid characters in domain"
		self.resource=s
	
	def __str__(self):
		return self.as_string()
	
	def __repr__(self):
		return "<JID: %r>" % (self.as_string())
	
	def as_string(self):
		return self.as_unicode().encode("utf-8")
		
	def as_unicode(self):
		if not self.node and not self.resource:
			return self.domain
		elif not self.node:
			return u"%s/%s" % (self.domain,self.resource)
		elif not self.resource:
			return u"%s@%s" % (self.node,self.domain)
		else:
			return "%s@%s/%s" % (self.node,self.domain,self.resource)
	def bare(self):
		return JID(self.node,self.domain)
	
