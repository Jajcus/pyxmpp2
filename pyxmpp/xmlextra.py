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
from pyxmpp import _xmlextra
from pyxmpp._xmlextra import error
import threading

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
    def _stanza_start(self,_doc,_node):
        """Process stanza start."""
        doc=libxml2.xmlDoc(_doc)
        node=libxml2.xmlNode(_node)
        self.stanza_start(doc,node)
    def _stanza_end(self,_doc,_node):
        """Process stanza end."""
        doc=libxml2.xmlDoc(_doc)
        node=libxml2.xmlNode(_node)
        self.stanza_end(doc,node)
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
    def stanza_start(self,doc,node):
        """Called when the start tag of a direct child of the root
        element is encountered in the stream.

        :Parameters:
            - `doc`: the document being parsed.
            - `node`: the (incomplete) element being processed
        :Types:
            - `doc`: `libxml2.xmlDoc`
            - `node`: `libxml2.xmlNode`"""
        print >>sys.stderr,"Unhandled stanza start",`node.serialize()`
    def stanza_end(self,doc,node):
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
        print >>sys.stderr,"Unhandled stanza end",`node.serialize()`
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

class StreamReader:
    """A simple push-parser interface for XML streams."""
    def __init__(self,handler):
        """Initialize `StreamReader` object.

        :Parameters:
            - `handler`: handler object for the stream content
        :Types:
            - `handler`: `StreamHandler` derived class
        """
        self.reader=_xmlextra.preparsing_reader_new(handler)
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

def remove_ns(node, ns):
    """Remove a namespace declaration from a node.

    Refuse to do so if the namespace is used somwhere in the subtree.

    :Parameters:
       - `node`: the node from which the declaration should be removed.
       - `ns`: the namespace to remove.
    :Types:
        - `node`: `libxml2.xmlNode`
        - `ns`: `libxml2.xmlNs`"""
    if ns is None:
        ns__o = None
    else:
        ns__o = ns._o
    if node is None:
        node__o = None
    else:
        node__o = node._o
    return _xmlextra.remove_ns(node__o,ns__o)

def replace_ns(node, old_ns,new_ns):
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
    return _xmlextra.replace_ns(node__o,old_ns__o,new_ns__o)

# vi: sts=4 et sw=4
