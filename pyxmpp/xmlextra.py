import sys
import libxml2
import _xmlextra

class StreamParseError(StandardError):
	pass

class StreamHandler:
	def _stream_start(self,_doc):
		doc=libxml2.xmlDoc(_doc)
		self.stream_start(doc)
	def _stream_end(self,_doc):
		doc=libxml2.xmlDoc(_doc)
		self.stream_end(doc)
	def _stanza_start(self,_doc,_node):
		doc=libxml2.xmlDoc(_doc)
		node=libxml2.xmlDoc(_node)
		self.stanza_start(doc,node)
	def _stanza_end(self,_doc,_node):
		doc=libxml2.xmlDoc(_doc)
		node=libxml2.xmlDoc(_node)
		self.stanza_end(doc,node)
	
	def stream_start(self,doc):
		print >>sys.stderr,"Unhandled stream start:",`doc.serialize()`
	def stream_end(self,doc):
		print >>sys.stderr,"Unhandled stream end",`doc.serialize()`
	def stanza_start(self,doc,node):
		print >>sys.stderr,"Unhandled stanza start",`node.serialize()`
	def stanza_end(self,doc,node):
		print >>sys.stderr,"Unhandled stanza end",`node.serialize()`
	def error(self,descr):
		raise StreamParseError,descr

class StreamReader:
	def __init__(self,handler):
		self.reader=_xmlextra.reader_new(handler)
	def __del__(self):
		del self.reader
	def doc(self):
		ret=self.reader.doc()
		if ret:
			return libxml2.xmlDoc(ret)
		else:
			return None
	def feed(self,s):
		return self.reader.feed(s)
		
def remove_ns(node, ns):
	"""This function removes namespace declaration from a node. It
	   will refuse to do so if the namespace is used somwhere in
	   the subtree. """
	if ns is None: ns__o = None
	else: ns__o = ns._o
	if node is None: node__o = None
	else: node__o = node._o
	return _xmlextra.remove_ns(node__o,ns__o)
		
def replace_ns(node, old_ns,new_ns):
	"""This function removes namespace declaration from a node. It
	   will refuse to do so if the namespace is used somwhere in
	   the subtree. """
	if old_ns is None: old_ns__o = None
	else: old_ns__o = old_ns._o
	if new_ns is None: new_ns__o = None
	else: new_ns__o = new_ns._o
	if node is None: node__o = None
	else: node__o = node._o
	return _xmlextra.replace_ns(node__o,old_ns__o,new_ns__o)
