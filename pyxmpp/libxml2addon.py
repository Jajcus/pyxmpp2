#
# This is highly modified part of libxml2 by Daniel Veillard.
# See libxml2addon/Copyright for libxml2 copyright details
#
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

"""An ugly hack to make pyxmpp work with not-patched libxml2.
Original libxml2 (at least its xmlreader interface) is not suitable for parsing
XMPP streams."""

import libxml2
from libxml2 import xmlNs,xmlDoc,xmlNode
import _libxml2addon

def _xmlStreamReaderErrorFunc((f,arg),msg,severity,locator):
    """Intermediate callback to wrap the locator"""
    return f(arg,msg,severity,xmlStreamReaderLocator(locator))

class xmlStreamReaderCore:
    def __init__(self, _obj=None):
        self.input = None
        if _obj != None:self._o = _obj;return
        self._o = None

    def __del__(self):
        if self._o != None:
            _libxml2addon.xmlFreeStreamReader(self._o)
        self._o = None

    def SetErrorHandler(self,f,arg):
        """Register an error handler that will be called back as
           f(arg,msg,severity,locator)."""
        if f is None:
            _libxml2addon.xmlStreamReaderSetErrorHandler(\
                self._o,None,None)
        else:
            _libxml2addon.xmlStreamReaderSetErrorHandler(\
                self._o,_xmlStreamReaderErrorFunc,(f,arg))

    def GetErrorHandler(self):
        """Return (f,arg) as previously registered with setErrorHandler
           or (None,None)."""
        f,arg = _libxml2addon.xmlStreamReaderGetErrorHandler(self._o)
        if f is None:
            return None,None
        else:
            # assert f is _xmlStreamReaderErrorFunc
            return arg

#
# Functions from module tree
#
def removeNs(self, ns):
	"""This function removes namespace declaration from a node. It
	   will refuse to do so if the namespace is used somwhere in
	   the subtree. """
	if ns is None: ns__o = None
	else: ns__o = ns._o
	ret = _libxml2addon.xmlRemoveNs(self._o, ns__o)
	if ret is None:raise treeError('xmlRemoveNs() failed')
	__tmp = xmlNode(_obj=ret)
	return __tmp

libxml2.xmlNode.removeNs=removeNs

def replaceNs(self, oldNs, newNs):
	"""This function replaces oldNs with newNs evereywhere within
	   the tree. oldNs declaration is left untouched. """
	if oldNs is None: oldNs__o = None
	else: oldNs__o = oldNs._o
	if newNs is None: newNs__o = None
	else: newNs__o = newNs._o
	ret = _libxml2addon.xmlReplaceNs(self._o, oldNs__o, newNs__o)
	if ret is None:raise treeError('xmlReplaceNs() failed')
	__tmp = libxml2.xmlNs(_obj=ret)
	return __tmp

libxml2.xmlNode.replaceNs=replaceNs

class xmlStreamReader(xmlStreamReaderCore):
    def __init__(self, _obj=None):
        self.input = None
        self._o = None
        xmlStreamReaderCore.__init__(self, _obj=_obj)

    def __del__(self):
        if self._o != None:
            _libxml2addon.xmlFreeStreamReader(self._o)
        self._o = None

    #
    # xmlStreamReader functions from module xmlreader
    #

    def AttributeCount(self):
        """Provides the number of attributes of the current node """
        ret = _libxml2addon.xmlStreamReaderAttributeCount(self._o)
        return ret

    def BaseUri(self):
        """The base URI of the node. """
        ret = _libxml2addon.xmlStreamReaderBaseUri(self._o)
        return ret

    def Close(self):
        """This method releases any resources allocated by the current
           instance changes the state to Closed and close any
           underlying input. """
        ret = _libxml2addon.xmlStreamReaderClose(self._o)
        return ret

    def CurrentDoc(self):
        """Hacking interface allowing to get the xmlDocPtr
           correponding to the current document being accessed by the
           xmlStreamReader. This is dangerous because the associated
           node may be destroyed on the next Reads. """
        ret = _libxml2addon.xmlStreamReaderCurrentDoc(self._o)
        if ret is None:raise treeError('xmlStreamReaderCurrentDoc() failed')
        __tmp = xmlDoc(_obj=ret)
        return __tmp

    def CurrentNode(self):
        """Hacking interface allowing to get the xmlNodePtr
           correponding to the current node being accessed by the
           xmlStreamReader. This is dangerous because the underlying
           node may be destroyed on the next Reads. """
        ret = _libxml2addon.xmlStreamReaderCurrentNode(self._o)
        if ret is None:raise treeError('xmlStreamReaderCurrentNode() failed')
        __tmp = xmlNode(_obj=ret)
        return __tmp

    def Depth(self):
        """The depth of the node in the tree. """
        ret = _libxml2addon.xmlStreamReaderDepth(self._o)
        return ret

    def Expand(self):
        """Reads the contents of the current node and the full
           subtree. It then makes the subtree availsble until the
           next xmlStreamReaderRead() call """
        ret = _libxml2addon.xmlStreamReaderExpand(self._o)
        if ret is None:raise treeError('xmlStreamReaderExpand() failed')
        __tmp = xmlNode(_obj=ret)
        return __tmp

    def GetAttribute(self, name):
        """Provides the value of the attribute with the specified
           qualified name. """
        ret = _libxml2addon.xmlStreamReaderGetAttribute(self._o, name)
        return ret

    def GetAttributeNo(self, no):
        """Provides the value of the attribute with the specified
           index relative to the containing element. """
        ret = _libxml2addon.xmlStreamReaderGetAttributeNo(self._o, no)
        return ret

    def GetAttributeNs(self, localName, namespaceURI):
        """Provides the value of the specified attribute """
        ret = _libxml2addon.xmlStreamReaderGetAttributeNs(self._o, localName, namespaceURI)
        return ret

    def GetParserProp(self, prop):
        """Read the parser internal property. """
        ret = _libxml2addon.xmlStreamReaderGetParserProp(self._o, prop)
        return ret

    def GetRemainder(self):
        """Method to get the remainder of the buffered XML. this
           method stops the parser, set its state to End Of File and
           return the input stream with what is left that the parser
           did not use. """
        ret = _libxml2addon.xmlStreamReaderGetRemainder(self._o)
        if ret is None:raise treeError('xmlStreamReaderGetRemainder() failed')
        __tmp = inputBuffer(_obj=ret)
        return __tmp

    def HasAttributes(self):
        """Whether the node has attributes. """
        ret = _libxml2addon.xmlStreamReaderHasAttributes(self._o)
        return ret

    def HasValue(self):
        """Whether the node can have a text value. """
        ret = _libxml2addon.xmlStreamReaderHasValue(self._o)
        return ret

    def IsDefault(self):
        """Whether an Attribute  node was generated from the default
           value defined in the DTD or schema. """
        ret = _libxml2addon.xmlStreamReaderIsDefault(self._o)
        return ret

    def IsEmptyElement(self):
        """Check if the current node is empty """
        ret = _libxml2addon.xmlStreamReaderIsEmptyElement(self._o)
        return ret

    def IsValid(self):
        """Retrieve the validity status from the parser context """
        ret = _libxml2addon.xmlStreamReaderIsValid(self._o)
        return ret

    def LocalName(self):
        """The local name of the node. """
        ret = _libxml2addon.xmlStreamReaderLocalName(self._o)
        return ret

    def LookupNamespace(self, prefix):
        """Resolves a namespace prefix in the scope of the current
           element. """
        ret = _libxml2addon.xmlStreamReaderLookupNamespace(self._o, prefix)
        return ret

    def MoveToAttribute(self, name):
        """Moves the position of the current instance to the attribute
           with the specified qualified name. """
        ret = _libxml2addon.xmlStreamReaderMoveToAttribute(self._o, name)
        return ret

    def MoveToAttributeNo(self, no):
        """Moves the position of the current instance to the attribute
           with the specified index relative to the containing
           element. """
        ret = _libxml2addon.xmlStreamReaderMoveToAttributeNo(self._o, no)
        return ret

    def MoveToAttributeNs(self, localName, namespaceURI):
        """Moves the position of the current instance to the attribute
           with the specified local name and namespace URI. """
        ret = _libxml2addon.xmlStreamReaderMoveToAttributeNs(self._o, localName, namespaceURI)
        return ret

    def MoveToElement(self):
        """Moves the position of the current instance to the node that
           contains the current Attribute  node. """
        ret = _libxml2addon.xmlStreamReaderMoveToElement(self._o)
        return ret

    def MoveToFirstAttribute(self):
        """Moves the position of the current instance to the first
           attribute associated with the current node. """
        ret = _libxml2addon.xmlStreamReaderMoveToFirstAttribute(self._o)
        return ret

    def MoveToNextAttribute(self):
        """Moves the position of the current instance to the next
           attribute associated with the current node. """
        ret = _libxml2addon.xmlStreamReaderMoveToNextAttribute(self._o)
        return ret

    def Name(self):
        """The qualified name of the node, equal to Prefix :LocalName. """
        ret = _libxml2addon.xmlStreamReaderName(self._o)
        return ret

    def NamespaceUri(self):
        """The URI defining the namespace associated with the node. """
        ret = _libxml2addon.xmlStreamReaderNamespaceUri(self._o)
        return ret

    def Next(self):
        """Skip to the node following the current one in document
           order while avoiding the subtree if any. """
        ret = _libxml2addon.xmlStreamReaderNext(self._o)
        return ret

    def NodeType(self):
        """Get the node type of the current node Reference:
           http://dotgnu.org/pnetlib-doc/System/Xml/XmlNodeType.html """
        ret = _libxml2addon.xmlStreamReaderNodeType(self._o)
        return ret

    def Normalization(self):
        """The value indicating whether to normalize white space and
           attribute values. Since attribute value and end of line
           normalizations are a MUST in the XML specification only
           the value true is accepted. The broken bahaviour of
           accepting out of range character entities like &#0; is of
           course not supported either. """
        ret = _libxml2addon.xmlStreamReaderNormalization(self._o)
        return ret

    def Prefix(self):
        """A shorthand reference to the namespace associated with the
           node. """
        ret = _libxml2addon.xmlStreamReaderPrefix(self._o)
        return ret

    def QuoteChar(self):
        """The quotation mark character used to enclose the value of
           an attribute. """
        ret = _libxml2addon.xmlStreamReaderQuoteChar(self._o)
        return ret

    def Read(self):
        """Moves the position of the current instance to the next node
           in the stream, exposing its properties. """
        ret = _libxml2addon.xmlStreamReaderRead(self._o)
        return ret

    def ReadAttributeValue(self):
        """Parses an attribute value into one or more Text and
           EntityReference nodes. """
        ret = _libxml2addon.xmlStreamReaderReadAttributeValue(self._o)
        return ret

    def ReadInnerXml(self):
        """Reads the contents of the current node, including child
           nodes and markup. """
        ret = _libxml2addon.xmlStreamReaderReadInnerXml(self._o)
        return ret

    def ReadOuterXml(self):
        """Reads the contents of the current node, including child
           nodes and markup. """
        ret = _libxml2addon.xmlStreamReaderReadOuterXml(self._o)
        return ret

    def ReadState(self):
        """Gets the read state of the reader. """
        ret = _libxml2addon.xmlStreamReaderReadState(self._o)
        return ret

    def ReadString(self):
        """Reads the contents of an element or a text node as a string. """
        ret = _libxml2addon.xmlStreamReaderReadString(self._o)
        return ret

    def RelaxNGSetSchema(self, schema):
        """Use RelaxNG to validate the document as it is processed.
           Activation is only possible before the first Read(). if
           @schema is None, then RelaxNG validation is desactivated.
           @ The @schema should not be freed until the reader is
           deallocated or its use has been deactivated. """
        if schema is None: schema__o = None
        else: schema__o = schema._o
        ret = _libxml2addon.xmlStreamReaderRelaxNGSetSchema(self._o, schema__o)
        return ret

    def RelaxNGValidate(self, rng):
        """Use RelaxNG to validate the document as it is processed.
           Activation is only possible before the first Read(). if
           @rng is None, then RelaxNG validation is desactivated. """
        ret = _libxml2addon.xmlStreamReaderRelaxNGValidate(self._o, rng)
        return ret

    def SetParserProp(self, prop, value):
        """Change the parser processing behaviour by changing some of
           its internal properties. Note that some properties can
           only be changed before any read has been done. """
        ret = _libxml2addon.xmlStreamReaderSetParserProp(self._o, prop, value)
        return ret

    def Value(self):
        """Provides the text value of the node if present """
        ret = _libxml2addon.xmlStreamReaderValue(self._o)
        return ret

    def XmlLang(self):
        """The xml:lang scope within which the node resides. """
        ret = _libxml2addon.xmlStreamReaderXmlLang(self._o)
        return ret

def newStreamReader(self, URI):
	"""Create an xmlStreamReader structure fed with @input """
	ret = _libxml2addon.xmlNewStreamReader(self._o, URI)
	if ret is None:raise treeError('xmlNewStreamReader() failed')
	__tmp = xmlStreamReader(_obj=ret)
	__tmp.input = self
	return __tmp

libxml2.inputBuffer.newStreamReader=newStreamReader
