import libxml2
import random

from utils import from_utf8,to_utf8
from types import StringType,UnicodeType
from jid import JID

COMMON_NS="http://www.bnet.pl/~jajcus/pyxmpp/common"
common_doc=libxml2.newDoc("1.0")
common_root=common_doc.newChild(None,"root",None)
common_ns=common_root.newNs(COMMON_NS,None)
common_root.setNs(common_ns)
common_xpath_ctxt = common_doc.xpathNewContext()
common_xpath_ctxt.xpathRegisterNs("common",common_ns.getContent())

class StanzaError(RuntimeError):
	pass

random.seed()
last_id=random.randrange(1000000)

def gen_id():
	global last_id
	last_id+=1
	return str(last_id)
	
class Stanza:
	stanza_type="Unknown"
	def __init__(self,name_node,**kw):
		global common_doc,common_ns
		self.error=None
		self.node=None
		
		if isinstance(name_node,Stanza):
			self.node=name_node.node.copyNode(1)
			common_doc.addChild(self.node)
		elif isinstance(name_node,libxml2.xmlNode):
			self.node=name_node.docCopyNode(common_doc,1)
			common_doc.addChild(self.node)
			ns=self.node.ns()
			if not ns.name:
				self.node.replaceNs(ns,common_ns)
				try:
					self.node.removeNs(ns)
				except:
					pass
		else:	
			self.node=common_doc.newChild(common_ns,name_node,None)
			self.node.setNs(common_ns)

		if kw.has_key("fr"):
			fr=kw["fr"]
			if fr is not None:
				if not isinstance(fr,JID):
					fr=JID(fr)
				self.node.setProp("from",fr.as_string())
		if kw.has_key("to"):
			to=kw["to"]
			if to is not None:
				if not isinstance(to,JID):
					to=JID(to)
				self.node.setProp("to",to.as_string())
		if kw.has_key("type"):
			typ=kw["type"]
			if typ:
				self.node.setProp("type",kw["type"])
		if kw.has_key("id"):
			id=kw["id"]
			if id:
				self.node.setProp("id",kw["id"])

		if (self.get_type()=="error"
			and (kw.has_key("error_class") or kw.has_key("error_cond"))):
			if not kw.has_key("error_class") or not kw.has_key("error_cond"):
				raise StanzaError,("Both class and condition or"
					" none of them are required for stanza type error")
			from error import ErrorNode
			self.error=ErrorNode(kw["error_class"],kw["error_cond"],parent=self.node)
			
	def __del__(self):
		if self.node:
			self.free()

	def free(self):
		if self.error:
			self.error.free_borrowed()
		self.node.unlinkNode()
		self.node.freeNode()
		self.node=None
		pass

	def serialize(self):
		return self.node.serialize()
			
	def get_node(self):
		return node
	def get_from(self):
		if self.node.hasProp("from"):
			return JID(self.node.prop("from"))
		else:
			return None
	def get_to(self):
		if self.node.hasProp("to"):
			return JID(self.node.prop("to"))
		else:
			return None
	def get_type(self):
		return self.node.prop("type")
	def get_id(self):
		return self.node.prop("id")
	def get_error(self):
		if self.error:
			return self.error
		common_xpath_ctxt.setContextNode(self.node)
		n=common_xpath_ctxt.xpathEval(u"common:error")
		if not n:
			raise StanzaError,"This stanza contains no error"
		from error import ErrorNode
		self.error=ErrorNode(n[0],copy=0)
		return self.error
	def set_from(self,fr):
		return self.node.setProp("from",fr)
	def set_to(self,to):
		return self.node.setProp("to",to)
	def set_type(self,type):
		return self.node.setProp("type",type)
	def set_id(self,id):
		return self.node.setProp("id",id)
	
	def set_content(self,content):
		while self.node.children:
			self.node.children.unlinkNode()
		if isistance(content,libxml2.xmlNode):
			self.node.addChild(content.docCopyNode(common_doc,1))
		else:
			self.node.setContent(content)
			
	def add_content(self,content):
		if isistance(content,libxml2.xmlNode):
			self.node.addChild(content.docCopyNode(common_doc,1))
		else:
			self.node.addContent(content)
			
	def set_new_content(self,ns_uri,name):
		while self.node.children:
			self.node.children.unlinkNode()
		return self.add_new_content(ns_uri,name)
	
	def add_new_content(self,ns_uri,name):
		c=self.node.newChild(None,name,None)
		if ns_uri:
			ns=c.newNs(ns_uri,None)
			c.setNs(ns)
		return c

	def xpath_eval(self,expr,namespaces=None):
		if not namespaces:
			common_xpath_ctxt.setContextNode(self.node)
			return common_xpath_ctxt.xpathEval(expr)
		ctxt = common_doc.xpathNewContext()
		ctxt.setContextNode(self.node)
		for prefix,uri in namespaces.items():
			if uri==None:
				uri=COMMON_NS
			ctxt.xpathRegisterNs(prefix,uri)
		ret=ctxt.xpathEval(expr)
		ctxt.xpathFreeContext()
		return ret

