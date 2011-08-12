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

"""TLS certificate handling.
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import sys
import logging
import ssl

from collections import defaultdict
from datetime import datetime

try:
    from pyasn1_modules.rfc2459 import Certificate
    HAVE_PYASN1 = True
except ImportError:
    HAVE_PYASN1 = False

from .jid import JID, are_domains_equal
from .exceptions import JIDError

logger = logging.getLogger("pyxmpp2.cert")

class CertificateData(object):
    """Certificate information interface.
    
    This class provides only that information from the certificate, which
    is provided by the python API.
    """
    def __init__(self):
        self.validated = False
        self.subject_name = None
        self.not_after = None
        self.common_names = None
        self.alt_names = {}

    @property
    def display_name(self):
        """Get human-readable subject name derived from the SubjectName 
        or SubjectAltName field.
        """
        if self.subject_name:
            return u", ".join( [ u", ".join(
                        [ u"{0}={1}".format(k,v) for k, v in dn_tuple ] ) 
                            for dn_tuple in self.subject_name ])
        for name_type in ("XmppAddr", "DNS", "SRV"):
            names = self.alt_names.get(name_type)
            if names:
                return names[0]
        return u"<unknown>"

    def get_jids(self):
        """Return JIDs for which this certificate is valid (except the domain
        wildcards).
        
        :Returtype: `list` of `JID`
        """
        result = []
        if "XmppAddr" in self.alt_names or "DNS" in self.alt_names:
            addrs =  self.alt_names.get("XmppAddr", []) + self.alt_names.get(
                                                                    "DNS", [])
        elif self.common_names:
            addrs = [addr for addr in self.common_names 
                                if "@" not in addr and "/" not in addr]
        else:
            return []
        for addr in addrs:
            try:
                jid = JID(addr)
                if jid not in result:
                    result.append(jid)
            except JIDError, err:
                logger.warning(u"Bad JID in the certificate: {0!r}: {1}"
                                                            .format(addr, err))
        return result

    def verify_server(self, server_name, srv_type = 'xmpp-client'):
        """Verify certificate for a server.

        :Parameters:
            - `server_name`: name of the server presenting the cerificate
            - `srv_type`: service type requested, as used in the SRV record
        :Types:
            - `server_name`: `unicode` or `JID`
            - `srv_type`: `unicode`

        :Return: `True` if the certificate is valid for given name, `False`
        otherwise.
        """
        # TODO: wildcards
        server_jid = JID(server_name)
        if "XmppAddr" not in self.alt_names and "DNS" not in self.alt_names \
                                and "SRV" not in self.alt_names:
            return self.verify_jid_against_common_name(server_jid)
        for name in self.alt_names.get("DNS", []) + self.alt_names.get(
                                                            "XmppAddr", []):
            try:
                jid = JID(name)
            except ValueError:
                continue
            if jid == server_jid:
                return True
        if srv_type:
            return self.verify_jid_against_srv_name(jid, srv_type)
        return False

    def verify_jid_against_common_name(self, jid):
        """Return `True` if jid is listed in the certificate commonName.

        :Parameters:
            - `jid`: JID requested (domain part only)
        :Types:
            - `jid`: `JID`

        :Returntype: `bool`
        """
        if not self.common_names:
            return False
        for name in self.common_names:
            try:
                cn_jid = JID(name)
            except ValueError:
                continue
            if jid == cn_jid:
                return True
        return False

    def verify_jid_against_srv_name(self, jid, srv_type):
        """Check if the cerificate is valid for given domain-only JID
        and a service type.

        :Parameters:
            - `jid`: JID requested (domain part only)
            - `srv_type`: service type, e.g. 'xmpp-client'
        :Types:
            - `jid`: `JID`
            - `srv_type`: `unicode`
        :Returntype: `bool`
        """
        srv_prefix = u"_" + srv_type + u"."
        srv_prefix_l = len(srv_prefix)
        for srv in self.alt_names.get("SRV", []):
            if not srv.startswith(srv_prefix):
                continue
            try:
                srv_jid = JID(srv[srv_prefix_l:])
            except ValueError:
                continue
            if srv_jid == jid:
                return True
        return False

    def verify_client(self, client_jid = None, domains = None):
        """Verify certificate for a client.

        :Parameters:
            - `client_jid`: client name requested. May be `None` to allow
              any name in one of the `domains`.
            - `domains`: list of domains we can handle.
        :Types:
            - `client_jid`: `JID`
            - `domains`: `list` of `unicode`

        :Return: one of the jids in the certificate or `None` is no authorized
        name is found.
        """
        jids = [jid for jid in self.get_jids() if jid.local]
        if not jids:
            return False
        if client_jid is not None and client_jid in jids:
            return client_jid
        if domains is None:
            return jids[0]
        for jid in jids:
            for domain in domains:
                if are_domains_equal(jid.domain, domain):
                    return jid
        return None

class BasicCertificateData(CertificateData):
    """Certificate information interface.
    
    This class provides only that information from the certificate, which
    is provided by the python API.
    """
    @classmethod
    def from_ssl_socket(cls, ssl_socket):
        """Load certificate data from an SSL socket.
        """
        cert = cls()
        data = ssl_socket.getpeercert()
        if not data:
            return cert
        cert.validated = True
        cert.subject_name = data.get('subject')
        cert.alt_names = defaultdict(list)
        if 'subjectAltName' in data:
            for name, value in data['subjectAltName']:
                cert.alt_names[name].append(value)
        if 'notAfter' in data:
            tstamp = ssl.cert_time_to_seconds(data['notAfter'])
            cert.not_after = datetime.fromtimestamp(tstamp)
        if sys.version_info.major < 3:
            cert._decode_names() # pylint: disable=W0212
        cert.common_names = []
        if cert.subject_name:
            for part in cert.subject_name:
                for name, value in part:
                    if name == 'commonName':
                        cert.common_names.append(value)
        return cert

    def _decode_names(self):
        """Decode names (hopefully ASCII or UTF-8) into Unicode.
        """
        if self.subject_name is not None:
            subject_name = []
            for part in self.subject_name:
                new_part = []
                for name, value in part:
                    try:
                        name = name.decode("utf-8")
                        value = value.decode("utf-8")
                    except UnicodeError:
                        continue
                    new_part.append((name, value))
                subject_name.append(tuple(new_part))
            self.subject_name = tuple(subject_name)
        for key, old in self.alt_names.items():
            new = []
            for name in old:
                try:
                    name = name.decode("utf-8")
                except UnicodeError:
                    continue
                new.append(name)
            self.alt_names[key] = new

    @classmethod
    def from_file(cls, filename):
        """Load certificate from a file.
        """
        # pylint: disable=W0613
        return cls()

def get_certificate_from_ssl_socket(ssl_socket):
    """Get certificate data from an SSL socket.
    """
    return BasicCertificateData.from_ssl_socket(ssl_socket)

def get_certificate_from_file(filename):
    """Get certificate data from a PEM file.
    """
    return BasicCertificateData.from_file(filename)


