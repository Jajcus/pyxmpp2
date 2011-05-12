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
    def __init__(self, stanza_namespace, extra_prefixes = None):
        self.stanza_namespace = stanza_namespace
        self._prefixes = dict(STANDARD_PREFIXES)
        if extra_prefixes:
            self._prefixes.update(extra_prefixes)
        self._prefixes[stanza_namespace] = None
        self._root_prefixes = None
        self._head_emitted = False
        self._next_id = 1

    def add_prefix(self, namespace, prefix):
        if namespace in (self.stanza_namespace, STREAM_NS):
            raise ValueError, ("Cannot add custom prefix for"
                                        " stream or stanza namespace")
        if not self._head_emitted and not prefix:
            raise ValueError, ("Cannot add an empty prefixe"
                                        " before stream head has been emitted")
        self._prefixes[namespace] = prefix

    def emit_head(self, stream_from, stream_to, version = u'1.0'):
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
        return u"</{0}:stream>".format(self._root_prefixes[STREAM_NS])

    def _make_prefixed(self, name, declared_prefixes, declarations):
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
        string = self._emit_element(element, level = 1, 
                                    declared_prefixes = self._root_prefixes)
        return remove_evil_characters(string)

# vi: sts=4 et sw=4
