#
# (C) Copyright 2003-2004 Jacek Konieczny <jajcus@jajcus.net>
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

"""Extension to libxml2 for XMPP stream and stanza processing"""

__revision__="$Id: xmlextra.py,v 1.15 2004/10/11 18:33:51 jajcus Exp $"
__docformat__="restructuredtext en"

import sys
import libxml2
import threading

common_doc = libxml2.newDoc("1.0")
common_root = common_doc.newChild(None,"root",None)
COMMON_NS = "http://pyxmpp.jabberstudio.org/xmlns/common"
common_ns = common_root.newNs(COMMON_NS, None)
common_root.setNs(common_ns)
common_doc.setRootElement(common_root)

class StreamParseError(StandardError):
    """Exception raised when invalid XML is being processed."""
    pass

class StreamHandler:
    """Base class for stream handler."""
    def __init__(self):
        pass
        
    def _stream_start(self,_doc):
        """Process stream start."""
        doc=libxml2.xmlDoc(_doc)
        self.stream_start(doc)
    
    def _stream_end(self,_doc):
        """Process stream end."""
        doc=libxml2.xmlDoc(_doc)
        self.stream_end(doc)
        
    def _stanza(self,_doc,_node):
        """Process complete stanza."""
        doc=libxml2.xmlDoc(_doc)
        node=libxml2.xmlNode(_node)
        self.stanza(doc,node)

    def stream_start(self,doc):
        """Called when the start tag of root element is encountered
        in the stream.

        :Parameters:
            - `doc`: the document being parsed.
        :Types:
            - `doc`: `libxml2.xmlDoc`"""
        print >>sys.stderr,"Unhandled stream start:",`doc.serialize()`
        
    def stream_end(self,doc):
        """Called when the end tag of root element is encountered
        in the stream.

        :Parameters:
            - `doc`: the document being parsed.
        :Types:
            - `doc`: `libxml2.xmlDoc`"""
        print >>sys.stderr,"Unhandled stream end",`doc.serialize()`
    
    def stanza(self,doc,node):
        """Called when the end tag of a direct child of the root
        element is encountered in the stream.

        Please note, that node will be removed from the document
        and freed after this method returns. If it is needed after
        that a copy must be made before the method returns.

        :Parameters:
            - `doc`: the document being parsed.
            - `node`: the (complete) element being processed
        :Types:
            - `doc`: `libxml2.xmlDoc`
            - `node`: `libxml2.xmlNode`"""
        print >>sys.stderr,"Unhandled stanza",`node.serialize()`
        
    def error(self,descr):
        """Called when an error is encountered in the stream.

        :Parameters:
            - `descr`: description of the error
        :Types:
            - `descr`: `str`"""
        raise StreamParseError,descr

try:
#########################################################################
# C-extension based workarounds for libxml2 limitations
#-------------------------------------------------------
    from pyxmpp import _xmlextra
    from pyxmpp._xmlextra import error
        
    _create_reader = _xmlextra.sax_reader_new

    def replace_ns(node, old_ns,new_ns):
        """Replace namespaces in a whole subtree.

        The old namespace declaration will be removed if present on the `node`.

        :Parameters:
           - `node`: the root of the subtree where namespaces should be replaced.
           - `old_ns`: the namespace to replace.
           - `new_ns`: the namespace to be used instead of old_ns.
        :Types:
            - `node`: `libxml2.xmlNode`
            - `old_ns`: `libxml2.xmlNs`
            - `new_ns`: `libxml2.xmlNs`

        Both old_ns and new_ns may be None meaning no namespace set."""
        if old_ns is None:
            old_ns__o = None
        else:
            old_ns__o = old_ns._o
        if new_ns is None:
            new_ns__o = None
        else:
            new_ns__o = new_ns._o
        if node is None:
            node__o = None
        else:
            node__o = node._o
        _xmlextra.replace_ns(node__o,old_ns__o,new_ns__o)
        if old_ns__o:
            _xmlextra.remove_ns(node__o,old_ns__o)

    pure_python = False

except ImportError:
#########################################################################
# Pure python implementation (slow workarounds for libxml2 limitations) 
#-----------------------------------------------------------------------
    class error(Exception):
        pass

    def _escape(data):
        data=data.replace("&","&amp;")
        data=data.replace("<","&lt;")
        data=data.replace(">","&gt;")
        data=data.replace("'","&apos;")
        data=data.replace('"',"&quot;")
        return data

    class _SAXCallback(libxml2.SAXCallback):
        def __init__(self, handler):
            self._handler = handler 
            self._head = ""
            self._tail = ""
            self._current = ""
            self._level = 0
            self._doc = None
            self._root = None
            
        def cdataBlock(self, data):
            if self._level>1:
                self._current += _escape(data)

        def characters(self, data):
            if self._level>1:
                self._current += _escape(data)

        def comment(self, content):
            pass

        def endDocument(self):
            pass

        def endElement(self, tag):
            self._current+="</%s>" % (tag,)
            self._level -= 1
            if self._level > 1:
                return
            if self._level==1:
                xml=self._head+self._current+self._tail
                doc=libxml2.parseDoc(xml)
                try:
                    node = doc.getRootElement().children
                    try:
                        node1 = node.docCopyNode(self._doc, 1)
                        try:
                            self._root.addChild(node1)
                            self._handler.stanza(self._doc, node1)
                        except:
                            node1.unlinkNode()
                            node1.freeNode()
                            del node1
                    finally:
                        del node
                finally:
                    doc.freeDoc()
            else:
                xml=self._head+self._tail
                doc=libxml2.parseDoc(xml)
                try:
                    self._handler.stream_end(self._doc)
                    self._doc.freeDoc()
                    self._doc = None
                    self._root = None
                finally:
                    doc.freeDoc()

        def error(self, msg):
            self._handler.error(msg)

        fatalError = error

        ignorableWhitespace = characters

        def reference(self, name):
            self._current += "&" + name + ";"

        def startDocument(self):
            pass

        def startElement(self, tag, attrs):
            s = "<"+tag
            if attrs:
                for a,v in attrs.items():
                    s+=" %s='%s'" % (a,_escape(v))
            s += ">"
            if self._level == 0:
                self._head = s
                self._tail = "</%s>" % (tag,)
                xml=self._head+self._tail
                self._doc = libxml2.parseDoc(xml)
                self._handler.stream_start(self._doc)
                self._root = self._doc.getRootElement()
            elif self._level == 1:
                self._current = s
            else:
                self._current += s
            self._level += 1

        def warning(self):
            pass

    class _PythonReader:
        def __init__(self,handler):
            self.handler = handler
            self.sax = _SAXCallback(handler)
            self.parser = libxml2.createPushParser(self.sax, '', 0, 'stream')

        def feed(self, data):
            return self.parser.parseChunk(data, len(data), 0)
        
    _create_reader = _PythonReader

    def _get_ns(node):
        try:
            return node.ns()
        except libxml2.treeError:
            return None

    def replace_ns(node, old_ns, new_ns):
        """Replace namespaces in a whole subtree.

        :Parameters:
           - `node`: the root of the subtree where namespaces should be replaced.
           - `old_ns`: the namespace to replace.
           - `new_ns`: the namespace to be used instead of old_ns.
        :Types:
            - `node`: `libxml2.xmlNode`
            - `old_ns`: `libxml2.xmlNs`
            - `new_ns`: `libxml2.xmlNs`

        Both old_ns and new_ns may be None meaning no namespace set."""

        old_ns_uri = old_ns.content
        old_ns_prefix = old_ns.name
        new_ns_uri = new_ns.content
        new_ns_prefix = new_ns.name

        ns = _get_ns(node)
        if ns and ns.content == old_ns_uri and ns.name == old_ns_prefix:
            node.setNs(new_ns)

        p = node.properties
        while p:
            ns = _get_ns(p)
            if ns and ns.content == old_ns_uri and ns.name == old_ns_prefix:
                p.setNs(new_ns)
            p = p.next

        n = node.children
        while n:
            if n.type == 'element':
                skip_element = False
                try:
                    nsd = n.nsDefs()
                except libxml2.treeError:
                    nsd = None
                while nsd:
                    if nsd.name == old_ns_prefix:
                        skip_element = True
                        break
                    nsd = nsd.next
                if not skip_element:
                    replace_ns(n, old_ns, new_ns)
            n = n.next

    pure_python = True

###########################################################
# Common code                                    
#-------------

class StreamReader:
    """A simple push-parser interface for XML streams."""
    def __init__(self,handler):
        """Initialize `StreamReader` object.

        :Parameters:
            - `handler`: handler object for the stream content
        :Types:
            - `handler`: `StreamHandler` derived class
        """
        self.reader=_create_reader(handler)
        self.lock=threading.RLock()
        self.in_use=0
    def doc(self):
        """Get the document being parsed.

        :return: the document.
        :returntype: `libxml2.xmlNode`"""
        ret=self.reader.doc()
        if ret:
            return libxml2.xmlDoc(ret)
        else:
            return None
    def feed(self,s):
        """Pass a string to the stream parser.

        Parameters:
            - `s`: string to parse.
        Types:
            - `s`: `str`

        :return: `None` on EOF, `False` when whole input was parsed and `True`
            if there is something still left in the buffer."""
        self.lock.acquire()
        if self.in_use:
            self.lock.release()
            raise StreamParseError,"StreamReader.feed() is not reentrant!"
        self.in_use=1
        try:
            return self.reader.feed(s)
        finally:
            self.in_use=0
            self.lock.release()


# vi: sts=4 et sw=4
