#
# (C) Copyright 2011 Jacek Konieczny <jajcus@jajcus.net>
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

"""XMPP serializer for ElementTree data.

XMPP has specific requirements for XML serialization. Predefined
namespace prefixes must be used, including no prefix for the stanza
namespace (which may be one of, at least, two different namespaces:
'jabber:client' and 'jabber:server')"""

from __future__ import absolute_import

import threading
import re
from xml.sax.saxutils import escape, quoteattr

from .constants import STANZA_NAMESPACES, STREAM_NS

__docformat__ = "restructuredtext en"

STANDARD_PREFIXES = {
        STREAM_NS: u'stream',
    }

EVIL_CHARACTERS_RE = re.compile(r"[\000-\010\013\014\016-\037]", re.UNICODE)

def remove_evil_characters(data):
    """Remove control characters (not allowed in XML) from a string."""
    return EVIL_CHARACTERS_RE.sub(u"\ufffd", data)

class XMPPSerializer(object):
    """Implementation of the XMPP serializer.

    Single instance of this class should be used for a single stream and never
    reused. It will keep track of prefixes declared on the root element and 
    used later."""
    def __init__(self, stanza_namespace, extra_prefixes = None):
        """
        :Parameters:
            - `stanza_namespace`: the default namespace used for XMPP stanzas.
            E.g. 'jabber:client' for c2s connections.
            - `extra_prefixes`: mapping of namespaces to prefixes (not the
              other way) to be used on the stream. These prefixes will be
              declared on the root element and used in all descendants. That
              may be used to optimize the stream for size.
        :Types:
            - `stanza_namespace`: `unicode`
            - `extra_prefixxes`: `unicode` to `unicode` mapping.
        """
        self.stanza_namespace = stanza_namespace
        self._prefixes = dict(STANDARD_PREFIXES)
        if extra_prefixes:
            self._prefixes.update(extra_prefixes)
        self._prefixes[stanza_namespace] = None
        self._root_prefixes = None
        self._head_emitted = False
        self._next_id = 1

    def add_prefix(self, namespace, prefix):
        """Add a new namespace prefix.

        If the root element has not yet been emitted the prefix will
        be declared there, otherwise the prefix will be declared on the
        top-most element using this namespace in every stanza.

        :Parameters:
            - `namespace`: the namespace URI
            - `prefix`: the prefix string
        :Types:
            - `namespace`: `unicode`
            - `prefix`: `unicode`
        """
        if namespace in (self.stanza_namespace, STREAM_NS):
            raise ValueError, ("Cannot add custom prefix for"
                                        " stream or stanza namespace")
        if not self._head_emitted and not prefix:
            raise ValueError, ("Cannot add an empty prefixe"
                                        " before stream head has been emitted")
        self._prefixes[namespace] = prefix

    def emit_head(self, stream_from, stream_to, version = u'1.0'):
        """Return the opening tag of the stream root element.

        :Parameters:
            - `stream_from`: the 'from' attribute of the stream. May be `None`.
            - `stream_to`: the 'to' attribute of the stream. May be `None`.
            - `version`: the 'version' of the stream.
        :Types:
            - `stream_from`: `unicode`
            - `stream_to`: `unicode`
            - `version`: `unicode`
        """
        tag = u"<{0}:stream version={1}".format(self._prefixes[STREAM_NS],
                                                        quoteattr(version))
        if stream_from:
            tag += u" from={0}".format(quoteattr(stream_from))
        if stream_to:
            tag += u" to={0}".format(quoteattr(stream_to))
        for namespace, prefix in self._prefixes.items():
            if prefix:
                tag += u' xmlns:{0}={1}'.format(prefix, quoteattr(namespace))
            else:
                tag += u' xmlns={1}'.format(prefix, quoteattr(namespace))
        tag += u">"
        self._root_prefixes = dict(self._prefixes)
        self._head_emitted = True
        return tag

    def emit_tail(self):
        """Return the end tag of the stream root element."""
        return u"</{0}:stream>".format(self._root_prefixes[STREAM_NS])

    def _make_prefixed(self, name, declared_prefixes, declarations):
        """Return namespace-prefixed tag or attribute name.
        
        Add appropriate declaration to `declarations` when neccessary.
        
        :Parameters:
            - `name`: ElementTree 'qname' ('{namespace-uri}local-name')
              to convert
            - `declared_prefixes`: mapping of prefixes already declared 
              at this scope
            - `declarations`: XMLNS declarations on the current element.
        :Types:
            - `name`: `unicode`
            - `declared_prefixes`: `unicode` to `unicode` dictionary
            - `declarations`: `unicode` to `unicode` dictionary

        :Returntype: `unicode`"""
        if name.startswith(u"{"):
            namespace, name = name[1:].split(u"}", 1)
            if namespace in STANZA_NAMESPACES:
                namespace = self.stanza_namespace
        else:
            namespace = self.stanza_namespace
        if namespace in declared_prefixes:
            prefix = None
        elif namespace in self._prefixes:
            prefix = self._prefixes[namespace]
            declarations[namespace] = prefix
            declared_prefixes[namespace] = prefix
        else:
            used_prefixes = set(self._prefixes.values()) 
            used_prefixes |= set(declared_prefixes.values())
            while True:
                prefix = u"ns{0}".format(self._next_id)
                self._next_id += 1
                if prefix not in used_prefixes:
                    break
            declarations[namespace] = prefix
            declared_prefixes[namespace] = prefix
        if prefix:
            return prefix + u":" + name
        else:
            return name

    def _emit_element(self, element, level, declared_prefixes):
        """"Recursive XML element serializer.

        :Parameters:
            - `element`: the element to serialize
            - `level`: nest level (0 - root element, 1 - stanzas, etc.)
            - `declared_prefixes`: namespace to prefix mapping of already
                declared prefixes.
        :Types:
            - `element`: `ElementTree.Element`
            - `level`: `int`
            - `declared_prefixes`: `unicode` to `unicode` dictionary

        :Return: serialized element
        :Returntype: `unicode`
        """
        declarations = {}
        declared_prefixes = dict(declared_prefixes)
        name = element.tag
        prefixed = self._make_prefixed(name, declared_prefixes, declarations)
        start_tag = u"<{0}".format(prefixed)
        end_tag = u"</{0}>".format(prefixed)
        for name, value in element.items():
            prefixed = self._make_prefixed(name, declared_prefixes,
                                                                declarations)
            start_tag += u' {0}={1}'.format(prefixed, quoteattr(value))
        for namespace, prefix in declarations.items():
            if prefix:
                start_tag += u' xmlns:{0}={1}'.format(prefix, quoteattr(
                                                                namespace))
            else:
                start_tag += u' xmlns={1}'.format(prefix, quoteattr(
                                                                namespace))
            for d_namespace, d_prefix in declared_prefixes.items():
                if (not prefix and not d_prefix) or d_prefix == prefix:
                    del declared_prefixes[d_namespace]
        children = []
        for child in element:
            children.append(self._emit_element(child, level +1,
                                                        declared_prefixes))
        if not children and not element.text:
            start_tag += u"/>"
            end_tag = u""
            text = u""
        else:
            start_tag += u">"
            if level > 0 and element.text:
                text = escape(element.text)
            else:
                text = u""
        if level > 1 and element.tail:
            tail = escape(element.tail)
        else:
            tail = u""
        return start_tag + text + u''.join(children) + end_tag + tail

    def emit_stanza(self, element):
        """"Serialize a stanza.

        Must be called after `self.emit_head`.

        :Parameters:
            - `element`: the element to serialize
        :Types:
            - `element`: `ElementTree.Element`

        :Return: serialized element
        :Returntype: `unicode`
        """
        if not self._head_emitted:
            raise RuntimeError, ".emit_head() must be called first."
        string = self._emit_element(element, level = 1, 
                                    declared_prefixes = self._root_prefixes)
        return remove_evil_characters(string)


# thread local data to store XMPPSerializer instance used by the `serialize`
# function
_THREAD = threading.local()
_THREAD.serializer = None

def serialize(element):
    """Serialize an XMPP element.

    Utility function for debugging or logging.

        :Parameters:
            - `element`: the element to serialize
        :Types:
            - `element`: `ElementTree.Element`

        :Return: serialized element
        :Returntype: `unicode`
    """
    # pylint: disable-msg=W0603
    global _THREAD
    if _THREAD.serializer is None:
        _THREAD.serializer = XMPPSerializer("jabber:client")
        _THREAD.serializer.emit_head(None, None)
    return _THREAD.serializer.emit_stanza(element)

# vi: sts=4 et sw=4
