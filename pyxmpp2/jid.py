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

"""jid -- XMPP address handling

Normative reference:
  - `RFC 6122 <http://xmpp.org/rfcs/rfc6122.html>`__
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import re
import weakref
import warnings
import socket
import logging

from encodings import idna

from .xmppstringprep import NODEPREP, RESOURCEPREP
from .exceptions import JIDError, StringprepError

logger = logging.getLogger("pyxmpp2.jid")

# to enforce the UseSTD3ASCIIRules flag of IDNA
GOOD_OUTER = u"[^\x00-\x2C\x2E-\x2F\x3A-\x40\x5B-\x60\x7B-\x7F-]"
GOOD_INNER = u"[^\x00-\x2C\x2E-\x2F\x3A-\x40\x5B-\x60\x7B-\x7F]"
STD3_LABEL_RE = re.compile(u"^{0}({1}*{0})?$".format(GOOD_OUTER, GOOD_INNER))

# '.' equivalents, according to IDNA
UNICODE_DOT_RE = re.compile(u"[\u3002\uFF0E\uFF61]")

def are_domains_equal(domain1, domain2):
    """Compare two International Domain Names.

    :Parameters:
        - `domain1`: domains name to compare
        - `domain2`: domains name to compare
    :Types:
        - `domain1`: `unicode`
        - `domain2`: `unicode`

    :return: True `domain1` and `domain2` are equal as domain names."""

    domain1 = domain1.encode("idna")
    domain2 = domain2.encode("idna")
    return domain1.lower() == domain2.lower()

def _validate_ip_address(family, address):
    """Check if `address` is valid IP address and return it, in a normalized
    form.

    :Parameters:
        - `family`: ``socket.AF_INET`` or ``socket.AF_INET6``
        - `address`: the IP address to validate
    """
    try:
        info = socket.getaddrinfo(address, 0, family, socket.SOCK_STREAM, 0,
                                                        socket.AI_NUMERICHOST)
    except socket.gaierror, err:
        logger.debug("gaierror: {0} for {1!r}".format(err, address))
        raise ValueError("Bad IP address")

    if not info:
        logger.debug("getaddrinfo result empty")
        raise ValueError("Bad IP address")
    addr = info[0][4]
    logger.debug(" got address: {0!r}".format(addr))

    try:
        return socket.getnameinfo(addr, socket.NI_NUMERICHOST)[0]
    except socket.gaierror, err:
        logger.debug("gaierror: {0} for {1!r}".format(err, addr))
        raise ValueError("Bad IP address")

class JID(object):
    """JID.

    :Ivariables:
        - `local`: localpart of the JID
        - `domain`: domainpart of the JID
        - `resource`: resourcepart of the JID

    JID objects are immutable. They are also cached for better performance.
    """
    cache = weakref.WeakValueDictionary()
    __slots__ = ("local", "domain", "resource", "__weakref__",)
    def __new__(cls, local_or_jid = None, domain = None, resource = None,
                                                                check = True):
        """Create a new JID object or take one from the cache.

        :Parameters:
            - `local_or_jid`: localpart of the JID, JID object to copy, or
              Unicode representation of the JID.
            - `domain`: domain part of the JID
            - `resource`: resource part of the JID
            - `check`: if `False` then JID is not checked for specifiaction
              compliance.
        """

        if isinstance(local_or_jid, JID):
            return local_or_jid

        if domain is None and resource is None:
            obj = cls.cache.get(unicode(local_or_jid))
            if obj:
                return obj

        obj = object.__new__(cls)

        if local_or_jid:
            local_or_jid = unicode(local_or_jid)
        if (local_or_jid and not domain and not resource):
            local, domain, resource = cls.__from_unicode(local_or_jid)
            cls.cache[local_or_jid] = obj
        else:
            if domain is None and resource is None:
                raise JIDError("At least domain must be given")
            if check:
                local = cls.__prepare_local(local_or_jid)
                domain = cls.__prepare_domain(domain)
                resource = cls.__prepare_resource(resource)
            else:
                local = local_or_jid
        object.__setattr__(obj, "local", local)
        object.__setattr__(obj, "domain", domain)
        object.__setattr__(obj, "resource", resource)
        return obj

    def __setattr__(self, name, value):
        raise RuntimeError("JID objects are immutable!")

    def __attribute_declarations__(self):
        # to make pylint happy
        self.local = u""
        self.domain = u""
        self.resource = u""

    @classmethod
    def __from_unicode(cls, data, check = True):
        """Return jid tuple from an Unicode string.

        :Parameters:
            - `data`: the JID string
            - `check`: when `False` then the JID is not checked for
              specification compliance.

        :Return: (localpart, domainpart, resourcepart) tuple"""
        parts1 = data.split(u"/", 1)
        parts2 = parts1[0].split(u"@", 1)
        if len(parts2) == 2:
            local = parts2[0]
            domain = parts2[1]
            if check:
                local = cls.__prepare_local(local)
                domain = cls.__prepare_domain(domain)
        else:
            local = None
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
            raise JIDError("Domain is required in JID.")
        return (local, domain, resource)

    @staticmethod
    def __prepare_local(data):
        """Prepare localpart of the JID

        :Parameters:
            - `data`: localpart of the JID
        :Types:
            - `data`: `unicode`

        :raise JIDError: if the local name is too long.
        :raise pyxmpp.xmppstringprep.StringprepError: if the
            local name fails Nodeprep preparation."""
        if not data:
            return None
        data = unicode(data)
        try:
            local = NODEPREP.prepare(data)
        except StringprepError, err:
            raise JIDError(u"Local part invalid: {0}".format(err))
        if len(local.encode("utf-8")) > 1023:
            raise JIDError(u"Local part too long")
        return local

    @staticmethod
    def __prepare_domain(data):
        """Prepare domainpart of the JID.

        :Parameters:
            - `data`: Domain part of the JID
        :Types:
            - `data`: `unicode`

        :raise JIDError: if the domain name is too long.
        """
        # pylint: disable=R0912
        if not data:
            raise JIDError("Domain must be given")
        data = unicode(data)
        if not data:
            raise JIDError("Domain must be given")
        if u'[' in data:
            if data[0] == u'[' and data[-1] == u']':
                try:
                    addr = _validate_ip_address(socket.AF_INET6, data[1:-1])
                    return "[{0}]".format(addr)
                except ValueError, err:
                    logger.debug("ValueError: {0}".format(err))
                    raise JIDError(u"Invalid IPv6 literal in JID domainpart")
            else:
                raise JIDError(u"Invalid use of '[' or ']' in JID domainpart")
        elif data[0].isdigit() and data[-1].isdigit():
            try:
                addr = _validate_ip_address(socket.AF_INET, data)
            except ValueError, err:
                logger.debug("ValueError: {0}".format(err))
        data = UNICODE_DOT_RE.sub(u".", data)
        data = data.rstrip(u".")
        labels = data.split(u".")
        try:
            labels = [idna.nameprep(label) for label in labels]
        except UnicodeError:
            raise JIDError(u"Domain name invalid")
        for label in labels:
            if not STD3_LABEL_RE.match(label):
                raise JIDError(u"Domain name invalid")
            try:
                idna.ToASCII(label)
            except UnicodeError:
                raise JIDError(u"Domain name invalid")
        domain = u".".join(labels)
        if len(domain.encode("utf-8")) > 1023:
            raise JIDError(u"Domain name too long")
        return domain

    @staticmethod
    def __prepare_resource(data):
        """Prepare the resourcepart of the JID.

        :Parameters:
            - `data`: Resourcepart of the JID

        :raise JIDError: if the resource name is too long.
        :raise pyxmpp.xmppstringprep.StringprepError: if the
            resourcepart fails Resourceprep preparation."""
        if not data:
            return None
        data = unicode(data)
        try:
            resource = RESOURCEPREP.prepare(data)
        except StringprepError, err:
            raise JIDError(u"Local part invalid: {0}".format(err))
        if len(resource.encode("utf-8")) > 1023:
            raise JIDError("Resource name too long")
        return resource

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
        warnings.warn("JID.as_string() is deprecated. Use unicode()"
                " or `as_utf8` instead.", DeprecationWarning, stacklevel=1)
        return self.as_utf8()

    def as_unicode(self):
        """Unicode string JID representation.

        :return: JID as Unicode string."""
        result = self.domain
        if self.local:
            result = self.local + u'@' + result
        if self.resource:
            result = result + u'/' + self.resource
        if not JID.cache.has_key(result):
            JID.cache[result] = self
        return result

    def bare(self):
        """Make bare JID made by removing resource from current `self`.

        :return: new JID object without resource part."""
        return JID(self.local, self.domain, check = False)

    def __eq__(self, other):
        if other is None:
            return False
        elif type(other) in (str, unicode):
            try:
                other = JID(other)
            except StandardError:
                return False
        elif not isinstance(other, JID):
            return False

        return (self.local == other.local
            and are_domains_equal(self.domain, other.domain)
            and self.resource == other.resource)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if other is None:
            return False
        return unicode(self) < unicode(other)

    def __gt__(self, other):
        if other is None:
            return True
        return unicode(self) > unicode(other)

    def __le__(self, other):
        if other is None:
            return False
        return unicode(self) <= unicode(other)

    def __ge__(self, other):
        if other is None:
            return True
        return unicode(self) >= unicode(other)

    def __hash__(self):
        return hash(self.local) ^ hash(self.domain) ^ hash(self.resource)

# vi: sts=4 et sw=4
