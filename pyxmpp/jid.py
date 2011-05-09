#
# (C) Copyright 2003-2011 Jacek Konieczny <jajcus@jajcus.net>
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
# pylint: disable-msg=W0232, E0201

"""jid -- Jabber ID handling

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import re
import weakref
import warnings

from encodings import idna

from .xmppstringprep import nodeprep,resourceprep
from .exceptions import JIDError

node_invalid_re = re.compile(ur"[" u'"' ur"&'/:<>@\s\x00-\x19]", re.UNICODE)
resource_invalid_re = re.compile(ur"[\s\x00-\x19]", re.UNICODE)

def are_domains_equal(domain1, domain2):
    """Compare two International Domain Names.

    :Parameters:
        - `a`,`b`: domains names to compare

    :return: True `a` and `b` are equal as domain names."""

    domain1 = domain1.encode("idna")
    domain2 = domain2.encode("idna")
    return domain1.lower() == domain2.lower()

class JID(object):
    """JID.

    :Ivariables:
        - `node`: node part of the JID
        - `domain`: domain part of the JID
        - `resource`: resource part of the JID

    JID objects are immutable. They are also cached for better performance.
    """
    cache = weakref.WeakValueDictionary()
    __slots__ = ("node", "domain", "resource", "__weakref__",)
    def __new__(cls, node_or_jid = None, domain = None, resource = None,
                                                                check = True):
        """Create a new JID object or take one from the cache.

        :Parameters:
            - `node_or_jid`: node part of the JID, JID object to copy, or
              Unicode representation of the JID.
            - `domain`: domain part of the JID
            - `resource`: resource part of the JID
            - `check`: if `False` then JID is not checked for specifiaction
              compliance.
        """

        if isinstance(node_or_jid, JID):
            return node_or_jid

        if domain is None and resource is None:
            obj = cls.cache.get(unicode(node_or_jid))
            if obj:
                return obj
            
        obj = object.__new__(cls)

        if node_or_jid:
            node_or_jid = unicode(node_or_jid)
        if (node_or_jid and not domain and not resource):
            node, domain, resource = cls.__from_unicode(node_or_jid)
            cls.cache[node_or_jid] = obj
        else:
            if domain is None and resource is None:
                raise JIDError,"At least domain must be given"
            if check:
                node = cls.__prepare_node(node_or_jid)
                domain = cls.__prepare_domain(domain)
                resource = cls.__prepare_resource(resource)
            else:
                node = node_or_jid
        object.__setattr__(obj, "node", node)
        object.__setattr__(obj, "domain", domain)
        object.__setattr__(obj, "resource", resource)
        return obj
    
    def __setattr__(self,name,value):
        raise RuntimeError,"JID objects are immutable!"

    @classmethod
    def __from_unicode(cls, data, check = True):
        """Return jid tuple from an Unicode string.

        :Parameters:
            - `data`: the JID string
            - `check`: when `False` then the JID is not checked for
              specification compliance.
              
        :Return: (node, domain, resource) tuple"""
        parts1 = data.split(u"/", 1)
        parts2 = parts1[0].split(u"@", 1)
        if len(parts2) == 2:
            node = parts2[0]
            domain = parts2[1]
            if check:
                node = cls.__prepare_node(node)
                domain = cls.__prepare_domain(domain)
        else:
            node = None
            domain = parts2[0]
            if check:
                domain = cls.__prepare_domain(domain)
        if len(parts1) == 2:
            resource = parts1[1]
            if check:
                resource = cls.__prepare_resource(parts1[1])
        else:
            resource = None
        if not domain:
            raise JIDError, "Domain is required in JID."
        return (node, domain, resource)

    @staticmethod
    def __prepare_node(data):
        """Prepare node part of the JID

        :Parameters:
            - `data`: Node part of the JID
        :Types:
            - `data`: unicode

        :raise JIDError: if the node name is too long.
        :raise pyxmpp.xmppstringprep.StringprepError: if the
            node name fails Nodeprep preparation."""
        if not data:
            return None

        data = unicode(data)
        node = nodeprep.prepare(data)
        if len(node.encode("utf-8")) > 1023:
            raise JIDError,"Node name too long"
        return node

    @staticmethod
    def __prepare_domain(data):
        """Prepare node part of the JID.

        :Parameters:
            - `data`: Domain part of the JID
        :Types:
            - `data`: unicode

        :raise JIDError: if the domain name is too long."""
        if not data:
            raise JIDError, "Domain must be given"
        data = unicode(data)
        labels = data.split(u".")
        labels = [idna.nameprep(label) for label in labels]
        domain = ".".join(labels)
        if len(domain.encode("utf-8")) > 1023:
            raise JIDError, "Domain name too long"
        return domain

    @staticmethod
    def __prepare_resource(data):
        """Prepare resource part of the JID.

        :Parameters:
            - `data`: Resource part of the JID

        :raise JIDError: if the resource name is too long.
        :raise pyxmpp.xmppstringprep.StringprepError: if the
            node name fails Resourceprep preparation."""
        if not data:
            return None
        data = unicode(data)
        resource = resourceprep.prepare(data)
        if len(resource.encode("utf-8")) > 1023:
            raise JIDError, "Resource name too long"
        return resource

    def __str__(self):
        warnings.warn("JIDs should not be used as strings",
                                    DeprecationWarning, stacklevel = 2)
        return self.as_utf8()

    def __unicode__(self):
        return self.as_unicode()

    def __repr__(self):
        return "JID(%r)" % (self.as_unicode())

    def as_utf8(self):
        """UTF-8 encoded JID representation.

        :return: UTF-8 encoded JID."""
        return self.as_unicode().encode("utf-8")

    def as_string(self):
        """UTF-8 encoded JID representation.

        *Deprecated* Always use Unicode objects, or `as_utf8` if you really want.

        :return: UTF-8 encoded JID."""
        warnings.warn("JID.as_string() is deprecated. Use unicode() or `as_utf8` instead.",
                 DeprecationWarning, stacklevel=1)
        return self.as_utf8()

    def as_unicode(self):
        """Unicode string JID representation.

        :return: JID as Unicode string."""
        result = self.domain
        if self.node:
            result = self.node + u'@' + result
        if self.resource:
            result = result + u'/' + self.resource
        if not JID.cache.has_key(result):
            JID.cache[result] = self
        return result

    def bare(self):
        """Make bare JID made by removing resource from current `self`.

        :return: new JID object without resource part."""
        return JID(self.node, self.domain, check = False)

    def __eq__(self, other):
        if other is None:
            return False
        elif type(other) in (str, unicode):
            try:
                other = JID(other)
            except:
                return False
        elif not isinstance(other,JID):
            return False

        return (self.node == other.node
            and are_domains_equal(self.domain, other.domain)
            and self.resource == other.resource)

    def __ne__(self,other):
        return not self.__eq__(other)

    def __cmp__(self, other):
        uni = self.as_unicode()
        return cmp(uni, other)

    def __hash__(self):
        return hash(self.node) ^ hash(self.domain) ^ hash(self.resource)

# vi: sts=4 et sw=4
