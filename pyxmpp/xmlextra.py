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

__revision__="$Id: xmlextra.py,v 1.12 2004/09/14 19:57:58 jajcus Exp $"
__docformat__="restructuredtext en"

import sys
import libxml2
from pyxmpp import _xmlextra
import threading

"""Extension to libxml2 for XMPP stream and stanza processing"""

class StreamParseError(StandardError):
    """Exception raised when invalid XML is being processed"""
    pass

class StreamHandler:
    """Base class for stream handler."""
    def _stream_start(self,_doc):
        doc=libxml2.xmlDoc(_doc)
        self.stream_start(doc)
    def _stream_end(self,_doc):
        doc=libxml2.xmlDoc(_doc)
        self.stream_end(doc)
    def _stanza_start(self,_doc,_node):
        doc=libxml2.xmlDoc(_doc)
        node=libxml2.xmlNode(_node)
        self.stanza_start(doc,node)
    def _stanza_end(self,_doc,_node):
        doc=libxml2.xmlDoc(_doc)
        node=libxml2.xmlNode(_node)
        self.stanza_end(doc,node)
    def _stanza(self,_doc,_node):
        doc=libxml2.xmlDoc(_doc)
        node=libxml2.xmlNode(_node)
        self.stanza(doc,node)

    def stream_start(self,doc):
        """Called when the start tag of root element is encountered
        in the stream.

        doc is the document being parsed"""
        print >>sys.stderr,"Unhandled stream start:",`doc.serialize()`
    def stream_end(self,doc):
        """Called when the end tag of root element is encountered
        in the stream.

        doc is the document being parsed"""
        print >>sys.stderr,"Unhandled stream end",`doc.serialize()`
    def stanza_start(self,doc,node):
        """Called when the start tag of a direct child of the root
        element is encountered in the stream.

        doc is the document being parsed
        node is the (incomplete) element being processed"""
        print >>sys.stderr,"Unhandled stanza start",`node.serialize()`
    def stanza_end(self,doc,node):
        """Called when the end tag of a direct child of the root
        element is encountered in the stream.

        doc is the document being parsed
        node is the (complete) element parsed

        Please note, that node will be removed from the document
        and freed after this method returns. If it is needed after
        that a copy must be made before the method returns."""
        print >>sys.stderr,"Unhandled stanza end",`node.serialize()`
    def stanza(self,doc,node):
        """Called when the end tag of a direct child of the root
        element is encountered in the stream.

        doc is the document being parsed
        node is the (complete) element parsed

        Please note, that node will be removed from the document
        and freed after this method returns. If it is needed after
        that a copy must be made before the method returns."""
        print >>sys.stderr,"Unhandled stanza",`node.serialize()`
    def error(self,desc):
        """Called when an error is encountered in the stream."""
        raise StreamParseError,descr

class StreamReader:
    def __init__(self,handler):
        self.reader=_xmlextra.preparsing_reader_new(handler)
        self.lock=threading.RLock()
        self.in_use=0
    def doc(self):
        ret=self.reader.doc()
        if ret:
            return libxml2.xmlDoc(ret)
        else:
            return None
    def feed(self,s):
        """Passes string s to the stream parser. Returns None on EOF,
           0 when whole input was parsed and 1 if there is something still left
           in the buffer"""
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
    """This function removes namespace declaration from a node. It
       will refuse to do so if the namespace is used somwhere in
       the subtree.

       node is the node from which the declaration should be removed
       ns is namespace to remove"""
    if ns is None: ns__o = None
    else: ns__o = ns._o
    if node is None: node__o = None
    else: node__o = node._o
    return _xmlextra.remove_ns(node__o,ns__o)

def replace_ns(node, old_ns,new_ns):
    """This function places namespaces in whole subtree.

       node is the root of the subtree where namespaces should be replaced
       old_ns is the namespace to replace
       new_ns is the namespace to be used instead of old_ns

       Both old_ns and new_ns may be None meaning no namespace set"""
    if old_ns is None: old_ns__o = None
    else: old_ns__o = old_ns._o
    if new_ns is None: new_ns__o = None
    else: new_ns__o = new_ns._o
    if node is None: node__o = None
    else: node__o = node._o
    return _xmlextra.replace_ns(node__o,old_ns__o,new_ns__o)
# vi: sts=4 et sw=4
