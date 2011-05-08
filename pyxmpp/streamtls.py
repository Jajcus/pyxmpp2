#
# (C) Copyright 2003-2010 Jacek Konieczny <jajcus@jajcus.net>
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
# pylint: disable-msg=W0201

"""TLS support for XMPP streams.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__docformat__="restructuredtext en"

import socket
import sys
import errno
import logging
import ssl
import warnings
import inspect
from ssl import SSLError

from pyxmpp.streambase import StreamBase,STREAM_NS
from pyxmpp.streambase import FatalStreamError,StreamEncryptionRequired
from pyxmpp.exceptions import TLSNegotiationFailed, TLSError, TLSNegotiatedButNotAvailableError
from pyxmpp.jid import JID

TLS_NS="urn:ietf:params:xml:ns:xmpp-tls"

tls_available = True


def _count_args(callable):
    """Utility function to count expected arguments of a callable"""
    vc_args = inspect.getargspec(callable)
    count = len(vc_args.args)
    if not hasattr(callable, "im_self"):
        return count
    if callable.im_self is None:
        return count
    return count - 1

class TLSSettings:
    """Storage for TLS-related settings of an XMPP stream.

       :Ivariables:
            - `require`: is TLS required
            - `verify_peer`: should the peer's certificate be verified
            - `cert_file`: path to own X.509 certificate
            - `key_file`: path to the private key for own X.509 certificate
            - `cacert_file`: path to a file with trusted CA certificates
            - `verify_callback`: callback function for certificate
              verification."""

    def __init__(self,
            require = False, verify_peer = True,
            cert_file = None, key_file = None, cacert_file = None,
            verify_callback = None, ctx = None):
        """Initialize the TLSSettings object.

        :Parameters:
            - `require`:  is TLS required
            - `verify_peer`: should the peer's certificate be verified
            - `cert_file`: path to own X.509 certificate
            - `key_file`: path to the private key for own X.509 certificate
            - `cacert_file`: path to a file with trusted CA certificates
            - `verify_callback`: callback function for certificate
              verification. The callback function must accept a single
              argument: the certificate to verify, as returned by
              `ssl.SSLSocket.getpeercert()` and return True if a certificate is
              accepted.  The verification callback should call
              Stream.tls_is_certificate_valid() to check if certificate subject
              name or alt subject name matches stream peer JID."""
        if ctx is not None:
             warnings.warn("ctx argument of TLSSettings is deprecated",
                                                        DeprecationWarning)
        self.require = require
        self.verify_peer = verify_peer
        self.cert_file = cert_file
        self.cacert_file = cacert_file
        self.key_file = key_file
        if verify_callback:
            if _count_args(verify_callback) > 1 :
                warnings.warn("Two-argument TLS verify callback is deprecated",
                                                        DeprecationWarning)
                verify_callback = None
        self.verify_callback = verify_callback

class StreamTLSMixIn:
    """Mix-in class providing TLS support for an XMPP stream.

    :Ivariables:
        - `tls`: TLS connection object.
    """
    def __init__(self, tls_settings = None):
        """Initialize TLS support of a Stream object

        :Parameters:
          - `tls_settings`: settings for StartTLS.
        :Types:
          - `tls_settings`: `TLSSettings`
        """
        self.tls_settings = tls_settings
        self.__logger = logging.getLogger("pyxmpp.StreamTLSMixIn")

    def _reset_tls(self):
        """Reset `StreamTLSMixIn` object state making it ready to handle new
        connections."""
        self.tls = None
        self.tls_requested = False

    def _make_stream_tls_features(self, features):
        """Update the <features/> with StartTLS feature.

        [receving entity only]

        :Parameters:
            - `features`: the <features/> element of the stream.
        :Types:
            - `features`: `libxml2.xmlNode`

        :returns: updated <features/> element node.
        :returntype: `libxml2.xmlNode`"""
        if self.tls_settings and not self.tls:
            tls = features.newChild(None, "starttls", None)
            ns = tls.newNs(TLS_NS, None)
            tls.setNs(ns)
            if self.tls_settings.require:
                tls.newChild(None, "required", None)
        return features

    def _write_raw(self,data):
        """Same as `Stream.write_raw` but assume `self.lock` is acquired."""
        logging.getLogger("pyxmpp.Stream.out").debug("OUT: %r",data)
        try:
            while self.socket:
                try:
                    while data:
                        sent = self.socket.send(data)
                        data = data[sent:]
                except SSLError, err:
                    if err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                        continue
                    raise
                break
        except (IOError, OSError, socket.error),e:
            raise FatalStreamError("IO Error: "+str(e))
        except SSLError,e:
            raise TLSError("TLS Error: "+str(e))

    def _read_tls(self):
        """Read data pending on the stream socket and pass it to the parser."""
        if self.eof:
            return
        while self.socket:
            try:
                r = self.socket.read()  # .recv() blocks in python 2.6.4
                if r is None:
                    return
            except SSLError, err:
                if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                    return
                raise
            except socket.error, err:
                if err.args[0] != errno.EINTR:
                    raise
                return
            self._feed_reader(r)

    def _read(self):
        """Read data pending on the stream socket and pass it to the parser."""
        self.__logger.debug("StreamTLSMixIn._read(), socket: %r",self.socket)
        if self.tls:
            self._read_tls()
        else:
            StreamBase._read(self)

    def _process(self):
        """Same as `Stream.process` but assume `self.lock` is acquired."""
        try:
            StreamBase._process(self)
        except SSLError,e:
            self.close()
            raise TLSError("TLS Error: "+str(e))

    def _process_node_tls(self,xmlnode):
        """Process incoming stream element. Pass it to _process_tls_node
        if it is in TLS namespace.

        :raise StreamEncryptionRequired: if encryption is required by current
          configuration, it is not active and the element is not in the TLS
          namespace nor in the stream namespace.

        :return: `True` when the node was recognized as TLS element.
        :returntype: `bool`"""
        ns_uri=xmlnode.ns().getContent()
        if ns_uri==STREAM_NS:
            return False
        elif ns_uri==TLS_NS:
            self._process_tls_node(xmlnode)
            return True
        if self.tls_settings and self.tls_settings.require and not self.tls:
            raise StreamEncryptionRequired,"TLS encryption required and not started yet"
        return False

    def _handle_tls_features(self):
        """Process incoming StartTLS related element of <stream:features/>.

        [initiating entity only]

        The received features node is available in `self.features`."""
        ctxt = self.doc_in.xpathNewContext()
        ctxt.setContextNode(self.features)
        ctxt.xpathRegisterNs("tls",TLS_NS)
        try:
            tls_n=ctxt.xpathEval("tls:starttls")
            tls_required_n=ctxt.xpathEval("tls:starttls/tls:required")
        finally:
            ctxt.xpathFreeContext()

        if not self.tls:
            if tls_required_n and not self.tls_settings:
                raise FatalStreamError,"StartTLS support disabled, but required by peer"
            if self.tls_settings and self.tls_settings.require and not tls_n:
                raise FatalStreamError,"StartTLS required, but not supported by peer"
            if self.tls_settings and tls_n:
                self.__logger.debug("StartTLS negotiated")
                if self.initiator:
                    self._request_tls()
            else:
                self.__logger.debug("StartTLS not negotiated")

    def _request_tls(self):
        """Request a TLS-encrypted connection.

        [initiating entity only]"""
        self.tls_requested=1
        self.features=None
        root=self.doc_out.getRootElement()
        xmlnode=root.newChild(None,"starttls",None)
        ns=xmlnode.newNs(TLS_NS,None)
        xmlnode.setNs(ns)
        self._write_raw(xmlnode.serialize(encoding="UTF-8"))
        xmlnode.unlinkNode()
        xmlnode.freeNode()

    def _process_tls_node(self,xmlnode):
        """Process stream element in the TLS namespace.

        :Parameters:
            - `xmlnode`: the XML node received
        """
        if not self.tls_settings or not tls_available:
            self.__logger.debug("Unexpected TLS node: %r" % (xmlnode.serialize()))
            return False
        if self.initiator:
            if xmlnode.name=="failure":
                raise TLSNegotiationFailed,"Peer failed to initialize TLS connection"
            elif xmlnode.name!="proceed" or not self.tls_requested:
                self.__logger.debug("Unexpected TLS node: %r" % (xmlnode.serialize()))
                return False
            try:
                self.tls_requested=0
                self._make_tls_connection()
                self.socket=self.tls
            except SSLError,e:
                self.tls=None
                raise TLSError("TLS Error: "+str(e))
            self.__logger.debug("Restarting XMPP stream")
            self._restart_stream()
            return True
        else:
            raise FatalStreamError,"TLS not implemented for the receiving side yet"

    def _make_tls_connection(self):
        """Initiate TLS connection.

        [initiating entity only]"""
        if not tls_available or not self.tls_settings:
            raise TLSError,"TLS is not available"

        self.state_change("tls connecting",self.peer)

        if not self.tls_settings.verify_callback:
            self.tls_settings.verify_callback = self.tls_is_certificate_valid
        
        self.__logger.debug("tls_settings: {0!r}".format(self.tls_settings.__dict__))
        self.__logger.debug("Creating TLS connection")

        if self.tls_settings.verify_peer:
            cert_reqs = ssl.CERT_REQUIRED
        else:
            cert_reqs = ssl.CERT_NONE

        self.tls = ssl.wrap_socket(self.socket,
                    keyfile = self.tls_settings.key_file,
                    certfile = self.tls_settings.cert_file,
                    server_side = not self.initiator,
                    cert_reqs = cert_reqs,
                    ssl_version = ssl.PROTOCOL_TLSv1,
                    ca_certs = self.tls_settings.cacert_file,
                    do_handshake_on_connect = False,
                    )
        self.socket = None
        self.__logger.debug("Starting TLS handshake")
        self.tls.do_handshake()
        self.tls.setblocking(False)
        if self.tls_settings.verify_peer:
            valid = self.tls_settings.verify_callback(self.tls.getpeercert())
            if not valid:
                raise SSLError, "Certificate verification failed"
        self.socket = self.tls
        self.state_change("tls connected", self.peer)

    def tls_is_certificate_valid(self, cert):
        """Default certificate verification callback for TLS connections.

        :Parameters:
            - `cert`: certificate information, as returned by `ssl.SSLSocket.getpeercert`

        :return: computed verification result."""
        try:
            self.__logger.debug("tls_is_certificate_valid(cert = %r)" % (
                                                                        cert,))
            if not cert:
                self.__logger.warning("No TLS certificate information received.")
                return False
            valid_hostname_found = False
            if 'subject' in cert:
                for rdns in cert['subject']:
                    for key, value in rdns:
                        if key == 'commonName' and JID(value) == self.peer:
                            self.__logger.debug(" good commonName: {0}".format(value))
                            valid_hostname_found = True
            if 'subjectAltName' in cert:
                for key, value in cert['subjectAltName']:
                    if key == 'DNS' and JID(value) == self.peer:
                        self.__logger.debug(" good subjectAltName({0}): {1}"
                                                                    .format(key, value))
                        valid_hostname_found = True
            return valid_hostname_found
        except:
            self.__logger.exception("Exception caught")
            raise

    def get_tls_connection(self):
        """Get the TLS connection object for the stream.

        :return: `self.tls`"""
        return self.tls

# vi: sts=4 et sw=4
