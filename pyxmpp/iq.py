
import libxml2

from utils import from_utf8,to_utf8
from stanza import Stanza,StanzaError,gen_id

class Iq(Stanza):
	stanza_type="iq"
	def __init__(self,node=None,**kw):
		self.node=None
		if isinstance(node,Iq):
			pass
		elif isinstance(node,Stanza):
			raise TypeError,"Couldn't make Iq from other Stanza"
		elif isinstance(node,libxml2.xmlNode):
			pass
		elif node is not None:
			raise TypeError,"Couldn't make Iq from %r" % (type(node),)
		elif not kw.has_key("type"):
			raise StanzaError,"type is required for Iq"
		else:
			if not kw.has_key("id"):
				kw["id"]=gen_id()
	
		if kw.has_key("type") and kw["type"] not in ("get","set","result","error"):
			raise StanzaError,"Invalid Iq type: %r" % (type,)

		if node is None:
			node="iq"
		apply(Stanza.__init__,[self,node],kw)

	def make_error_reply(self,clas,cond):
		if self.get_type() not in ("set","get"):
			raise StanzaError,"Errors may only be generated for 'set' or 'get' iq"
		
		iq=Iq(type="error",fr=self.get_to(),to=self.get_from(),
			id=self.get_id(),error_class=clas,error_cond=cond)
		n=self.get_query().copyNode(1)
		print iq.serialize()
		iq.node.children.addPrevSibling(n)
		return iq
	
	def make_result_reply(self):
		if self.get_type() not in ("set","get"):
			raise StanzaError,"Results may only be generated for 'set' or 'get' iq"
		
		iq=Iq(type="result",fr=self.get_to(),to=self.get_from(),id=self.get_id())
		return iq

	def new_query(self,ns_uri,name="query"):
		return self.set_new_content(ns_uri,name)
		
	def get_query(self):
		for c in self.node.xpathEval("*"):
			if c.ns()!=self.node.ns():
				return c
		raise StanzaError,"This iq stanza doesn't contain any query"

	def get_query_ns(self):
		return self.get_query().ns().getContent()
