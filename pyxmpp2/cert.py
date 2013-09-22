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
    import pyasn1  # pylint: disable=W0611
    import pyasn1_modules.rfc2459  # pylint: disable=W0611
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
        if ("XmppAddr" in self.alt_names or "DNS" in self.alt_names
                                            or "SRVName" in self.alt_names):
            addrs =  self.alt_names.get("XmppAddr", [])
            addrs += [ addr for addr in self.alt_names.get("DNS", [])
                                            if not addr.startswith("*.") ]
            addrs += [ addr.split(".", 1)[1] for addr
                                        in self.alt_names.get("SRVName", [])
                            if (addr.startswith("_xmpp-server.")
                                    or addr.startswith("_xmpp-client."))]
            warn_bad = True
        elif self.common_names:
            addrs = [addr for addr in self.common_names
                                if "@" not in addr and "/" not in addr]
            warn_bad = False
        else:
            return []
        for addr in addrs:
            try:
                jid = JID(addr)
                if jid not in result:
                    result.append(jid)
            except JIDError, err:
                if warn_bad:
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
        server_jid = JID(server_name)
        if "XmppAddr" not in self.alt_names and "DNS" not in self.alt_names \
                                and "SRV" not in self.alt_names:
            return self.verify_jid_against_common_name(server_jid)
        names = [name for name in self.alt_names.get("DNS", [])
                                        if not name.startswith(u"*.")]
        names += self.alt_names.get("XmppAddr", [])
        for name in names:
            logger.debug("checking {0!r} against {1!r}".format(server_jid,
                                                                name))
            try:
                jid = JID(name)
            except ValueError:
                logger.debug("Not a valid JID: {0!r}".format(name))
                continue
            if jid == server_jid:
                logger.debug("Match!")
                return True
        if srv_type and self.verify_jid_against_srv_name(server_jid, srv_type):
            return True
        wildcards = [name[2:] for name in self.alt_names.get("DNS", [])
                                                if name.startswith("*.")]
        if not wildcards or not "." in server_jid.domain:
            return False
        logger.debug("checking {0!r} against wildcard domains: {1!r}"
                                                .format(server_jid, wildcards))
        server_domain = JID(domain = server_jid.domain.split(".", 1)[1])
        for domain in wildcards:
            logger.debug("checking {0!r} against {1!r}".format(server_domain,
                                                                domain))
            try:
                jid = JID(domain)
            except ValueError:
                logger.debug("Not a valid JID: {0!r}".format(name))
                continue
            if jid == server_domain:
                logger.debug("Match!")
                return True
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
        for srv in self.alt_names.get("SRVName", []):
            logger.debug("checking {0!r} against {1!r}".format(jid,
                                                                srv))
            if not srv.startswith(srv_prefix):
                logger.debug("{0!r} does not start with {1!r}"
                                                .format(srv, srv_prefix))
                continue
            try:
                srv_jid = JID(srv[srv_prefix_l:])
            except ValueError:
                continue
            if srv_jid == jid:
                logger.debug("Match!")
                return True
        return False

    def verify_client(self, client_jid = None, domains = None):
        """Verify certificate for a client.

        Please note that `client_jid` is only a hint to choose from the names,
        other JID may be returned if `client_jid` is not included in the
        certificate.

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
            return None
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
        try:
            data = ssl_socket.getpeercert()
        except AttributeError:
            # PyPy doesn't have .getppercert
            return cert
        logger.debug("Certificate data from ssl module: {0!r}".format(data))
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
            cert.not_after = datetime.utcfromtimestamp(tstamp)
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

DN_OIDS = {
        (2, 5, 4, 41): u"name",
        (2, 5, 4, 4): u"surname",
        (2, 5, 4, 42): u"givenName",
        (2, 5, 4, 43): u"initials",
        (2, 5, 4, 3): u"commonName",
        (2, 5, 4, 7): u"localityName",
        (2, 5, 4, 8): u"stateOrProvinceName",
        (2, 5, 4, 10): u"organizationName",
        (2, 5, 4, 11): u"organizationalUnitName",
        (2, 5, 4, 12): u"title",
        (2, 5, 4, 6): u"countryName",
}

def _decode_asn1_string(data):
    """Convert ASN.1 string to a Unicode string.
    """
    if isinstance(data, BMPString):
        return bytes(data).decode("utf-16-be")
    else:
        return bytes(data).decode("utf-8")

if HAVE_PYASN1:
    from pyasn1_modules.rfc2459 import Certificate, DirectoryString, MAX, Name
    from pyasn1_modules import pem
    from pyasn1.codec.der import decoder as der_decoder
    from pyasn1.type.char import BMPString, IA5String, UTF8String
    from pyasn1.type.univ import Sequence, SequenceOf, Choice
    from pyasn1.type.univ import Any, ObjectIdentifier, OctetString
    from pyasn1.type.namedtype import NamedTypes, NamedType
    from pyasn1.type.useful import GeneralizedTime
    from pyasn1.type.constraint import ValueSizeConstraint
    from pyasn1.type import tag

    XMPPADDR_OID = ObjectIdentifier('1.3.6.1.5.5.7.8.5')
    SRVNAME_OID = ObjectIdentifier('1.3.6.1.5.5.7.8.7')
    SUBJECT_ALT_NAME_OID = ObjectIdentifier('2.5.29.17')

    class OtherName(Sequence):
        # pylint: disable=C0111,R0903
        componentType = NamedTypes(
                NamedType('type-id', ObjectIdentifier()),
                NamedType('value', Any().subtype(explicitTag = tag.Tag(
                                tag.tagClassContext, tag.tagFormatSimple, 0)))
                )

    class GeneralName(Choice):
        # pylint: disable=C0111,R0903
        componentType = NamedTypes(
                NamedType('otherName',
                    OtherName().subtype(implicitTag = tag.Tag(
                        tag.tagClassContext, tag.tagFormatSimple, 0))),
                NamedType('rfc822Name',
                    IA5String().subtype(implicitTag = tag.Tag(
                        tag.tagClassContext, tag.tagFormatSimple, 1))),
                NamedType('dNSName',
                    IA5String().subtype(implicitTag = tag.Tag(
                        tag.tagClassContext, tag.tagFormatSimple, 2))),
                NamedType('x400Address',
                    OctetString().subtype(implicitTag = tag.Tag(
                        tag.tagClassContext, tag.tagFormatSimple, 3))),
                NamedType('directoryName',
                    Name().subtype(implicitTag = tag.Tag(
                        tag.tagClassContext, tag.tagFormatSimple, 4))),
                NamedType('ediPartyName',
                    OctetString().subtype(implicitTag = tag.Tag(
                        tag.tagClassContext, tag.tagFormatSimple, 5))),
                NamedType('uniformResourceIdentifier',
                    IA5String().subtype(implicitTag = tag.Tag(
                        tag.tagClassContext, tag.tagFormatSimple, 6))),
                NamedType('iPAddress',
                    OctetString().subtype(implicitTag = tag.Tag(
                        tag.tagClassContext, tag.tagFormatSimple, 7))),
                NamedType('registeredID',
                    ObjectIdentifier().subtype(implicitTag = tag.Tag(
                        tag.tagClassContext, tag.tagFormatSimple, 8))),
                )

    class GeneralNames(SequenceOf):
        # pylint: disable=C0111,R0903
        componentType = GeneralName()
        sizeSpec = SequenceOf.sizeSpec + ValueSizeConstraint(1, MAX)


class ASN1CertificateData(CertificateData):
    """Certificate information interface.

    This class actually decodes the certificate, providing all the
    names there.
    """
    _cert_asn1_type = None
    @classmethod
    def from_ssl_socket(cls, ssl_socket):
        """Get certificate data from an SSL socket.
        """
        try:
            data = ssl_socket.getpeercert(True)
        except AttributeError:
            # PyPy doesn't have .getpeercert
            data = None
        if not data:
            logger.debug("No certificate infromation")
            return cls()
        result = cls.from_der_data(data)
        result.validated = bool(ssl_socket.getpeercert())
        return result

    @classmethod
    def from_der_data(cls, data):
        """Decode DER-encoded certificate.

        :Parameters:
            - `data`: the encoded certificate
        :Types:
            - `data`: `bytes`

        :Return: decoded certificate data
        :Returntype: ASN1CertificateData
        """
        # pylint: disable=W0212
        logger.debug("Decoding DER certificate: {0!r}".format(data))
        if cls._cert_asn1_type is None:
            cls._cert_asn1_type = Certificate()
        cert = der_decoder.decode(data, asn1Spec = cls._cert_asn1_type)[0]
        result = cls()
        tbs_cert = cert.getComponentByName('tbsCertificate')
        subject = tbs_cert.getComponentByName('subject')
        logger.debug("Subject: {0!r}".format(subject))
        result._decode_subject(subject)
        validity = tbs_cert.getComponentByName('validity')
        result._decode_validity(validity)
        extensions = tbs_cert.getComponentByName('extensions')
        if extensions:
            for extension in extensions:
                logger.debug("Extension: {0!r}".format(extension))
                oid = extension.getComponentByName('extnID')
                logger.debug("OID: {0!r}".format(oid))
                if oid != SUBJECT_ALT_NAME_OID:
                    continue
                value = extension.getComponentByName('extnValue')
                logger.debug("Value: {0!r}".format(value))
                if isinstance(value, Any):
                    # should be OctetString, but is Any
                    # in pyasn1_modules-0.0.1a
                    value = der_decoder.decode(value,
                                                asn1Spec = OctetString())[0]
                alt_names = der_decoder.decode(value,
                                            asn1Spec = GeneralNames())[0]
                logger.debug("SubjectAltName: {0!r}".format(alt_names))
                result._decode_alt_names(alt_names)
        return result

    def _decode_subject(self, subject):
        """Load data from a ASN.1 subject.
        """
        self.common_names = []
        subject_name = []
        for rdnss in subject:
            for rdns in rdnss:
                rdnss_list = []
                for nameval in rdns:
                    val_type = nameval.getComponentByName('type')
                    value = nameval.getComponentByName('value')
                    if val_type not in DN_OIDS:
                        logger.debug("OID {0} not supported".format(val_type))
                        continue
                    val_type = DN_OIDS[val_type]
                    value = der_decoder.decode(value,
                                            asn1Spec = DirectoryString())[0]
                    value = value.getComponent()
                    try:
                        value = _decode_asn1_string(value)
                    except UnicodeError:
                        logger.debug("Cannot decode value: {0!r}".format(value))
                        continue
                    if val_type == u"commonName":
                        self.common_names.append(value)
                    rdnss_list.append((val_type, value))
                subject_name.append(tuple(rdnss_list))
        self.subject_name = tuple(subject_name)

    def _decode_validity(self, validity):
        """Load data from a ASN.1 validity value.
        """
        not_after = validity.getComponentByName('notAfter')
        not_after = str(not_after.getComponent())
        if isinstance(not_after, GeneralizedTime):
            self.not_after = datetime.strptime(not_after, "%Y%m%d%H%M%SZ")
        else:
            self.not_after = datetime.strptime(not_after, "%y%m%d%H%M%SZ")
        self.alt_names = defaultdict(list)

    def _decode_alt_names(self, alt_names):
        """Load SubjectAltName from a ASN.1 GeneralNames value.

        :Values:
            - `alt_names`: the SubjectAltNama extension value
        :Types:
            - `alt_name`: `GeneralNames`
        """
        for alt_name in alt_names:
            tname = alt_name.getName()
            comp = alt_name.getComponent()
            if tname == "dNSName":
                key = "DNS"
                value = _decode_asn1_string(comp)
            elif tname == "uniformResourceIdentifier":
                key = "URI"
                value = _decode_asn1_string(comp)
            elif tname == "otherName":
                oid = comp.getComponentByName("type-id")
                value = comp.getComponentByName("value")
                if oid == XMPPADDR_OID:
                    key = "XmppAddr"
                    value = der_decoder.decode(value,
                                            asn1Spec = UTF8String())[0]
                    value = _decode_asn1_string(value)
                elif oid == SRVNAME_OID:
                    key = "SRVName"
                    value = der_decoder.decode(value,
                                            asn1Spec = IA5String())[0]
                    value = _decode_asn1_string(value)
                else:
                    logger.debug("Unknown other name: {0}".format(oid))
                    continue
            else:
                logger.debug("Unsupported general name: {0}"
                                                        .format(tname))
                continue
            self.alt_names[key].append(value)

    @classmethod
    def from_file(cls, filename):
        """Load certificate from a file.
        """
        with open(filename, "r") as pem_file:
            data = pem.readPemFromFile(pem_file)
        return cls.from_der_data(data)

if HAVE_PYASN1:
    def get_certificate_from_ssl_socket(ssl_socket):
        """Get certificate data from an SSL socket.
        """
        return ASN1CertificateData.from_ssl_socket(ssl_socket)
else:
    def get_certificate_from_ssl_socket(ssl_socket):
        """Get certificate data from an SSL socket.
        """
        return BasicCertificateData.from_ssl_socket(ssl_socket)

def get_certificate_from_file(filename):
    """Get certificate data from a PEM file.
    """
    return ASN1CertificateData.from_file(filename)
