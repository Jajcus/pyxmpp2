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

"""TLS support for XMPP streams.

Normative reference: 
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__ 
"""

__revision__="$Id: streamtls.py,v 1.3 2004/10/07 22:22:36 jajcus Exp $"
__docformat__="restructuredtext en"

import socket
import sys
import errno
import logging

from pyxmpp.streambase import StreamBase,STREAM_NS
from pyxmpp.streambase import FatalStreamError,StreamEncryptionRequired

try:
    from M2Crypto import SSL
    from M2Crypto.SSL import SSLError
    import M2Crypto.SSL.cb
    tls_available=1
except ImportError:
    tls_available=0
    class SSLError(Exception):
        "dummy"
        pass

TLS_NS="urn:ietf:params:xml:ns:xmpp-tls"

class TLSNegotiationFailed(FatalStreamError):
    """Raised when stream TLS negotiation fails."""
    pass

class TLSError(FatalStreamError):
    """Raised on TLS error during stream processing."""
    pass

class TLSSettings:
    """Storage for TLS-related settings of an XMPP stream.

       :Ivariables:
            - `require`: is TLS required
            - `verify_peer`: should the peer's certificate be verified
            - `cert_file`: path to own X.509 certificate
            - `key_file`: path to the private key for own X.509 certificate
            - `cacert_file`: path to a file with trusted CA certificates
            - `verify_callback`: callback function for certificate
              verification. See M2Crypto documentation for details."""

    def __init__(self,
            require=False,verify_peer=True,
            cert_file=None,key_file=None,cacert_file=None,
            verify_callback=None,ctx=None):
        """Initialize the TLSSettings object.
        
        :Parameters:
            - `require`:  is TLS required
            - `verify_peer`: should the peer's certificate be verified
            - `cert_file`: path to own X.509 certificate
            - `key_file`: path to the private key for own X.509 certificate
            - `cacert_file`: path to a file with trusted CA certificates
            - `verify_callback`: callback function for certificate
              verification. See M2Crypto documentation for details."""
        self.require=require
        self.ctx=ctx
        self.verify_peer=verify_peer
        self.cert_file=cert_file
        self.cacert_file=cacert_file
        self.key_file=key_file
        self.verify_callback=verify_callback

class StreamTLSMixIn:
    """Mix-in class providing TLS support for an XMPP stream.
    
    :Ivariables:
        - `tls`: TLS connection object.
    """
    def __init__(self,tls_settings=None):
        """Initialize TLS support of a Stream object

        :Parameters:
          - `tls_settings`: settings for StartTLS.
        :Types:
          - `tls_settings`: `TLSSettings`
        """
        self.tls_settings=tls_settings
        self.__logger=logging.getLogger("pyxmpp.StreamTLSMixIn")

    def _reset_tls(self):
        """Reset `StreamTLSMixIn` object state making it ready to handle new
        connections."""
        self.tls=None
        self.tls_requested=False

    def _make_stream_tls_features(self,features):
        """Update the <features/> with StartTLS feature.

        [receving entity only]

        :Parameters:
            - `features`: the <features/> element of the stream.
        :Types:
            - `features`: `libxml2.xmlNode`
        
        :returns: updated <features/> element node.
        :returntype: `libxml2.xmlNode`"""
        if self.tls_settings and not self.tls:
            tls=features.newChild(None,"starttls",None)
            ns=tls.newNs(TLS_NS,None)
            tls.setNs(ns)
            if self.tls_settings.require:
                tls.newChild(ns,"required",None)
        return features

    def _write_raw(self,data):
        """Same as `Stream.write_raw` but assume `self.lock` is acquired."""
        try:
            StreamBase._write_raw(self,data)
        except SSLError,e:
            raise TLSError("TLS Error: "+str(e))

    def _read_tls(self):
        """Read data pending on the stream socket and pass it to the parser."""
        if self.eof:
            return
        try:
            r=self.socket.read()
            if r is None:
                return
        except socket.error,e:
            if e.args[0]!=errno.EINTR:
                raise
            return
        self._feed_reader(r)

    def _read(self):
        """Read data pending on the stream socket and pass it to the parser."""
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

    def _process_node_tls(self,node):
        """Process incoming stream element. Pass it to _process_tls_node
        if it is in TLS namespace. 

        :raise StreamEncryptionRequired: if encryption is required by current
          configuration, it is not active and the element is not in the TLS
          namespace nor in the stream namespace.
        
        :return: `True` when the node was recognized as TLS element.
        :returntype: `bool`"""
        ns_uri=node.ns().getContent()
        if ns_uri==STREAM_NS:
            return False
        elif ns_uri==TLS_NS:
            self._process_tls_node(node)
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
                if not tls_available:
                    raise FatalStreamError,("StartTLS negotiated, but not available"
                            " (M2Crypto module required)")
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
        node=root.newChild(None,"starttls",None)
        ns=node.newNs(TLS_NS,None)
        node.setNs(ns)
        self._write_raw(node.serialize(encoding="UTF-8"))
        node.unlinkNode()
        node.freeNode()

    def _process_tls_node(self,node):
        """Process stream element in the TLS namespace.
        
        :Parameters:
            - `node`: the XML node received
        """
        if not self.tls_settings or not tls_available:
            self.__logger.debug("Unexpected TLS node: %r" % (node.serialize()))
            return False
        if self.initiator:
            if node.name=="failure":
                raise TLSNegotiationFailed,"Peer failed to initialize TLS connection"
            elif node.name!="proceed" or not self.tls_requested:
                self.__logger.debug("Unexpected TLS node: %r" % (node.serialize()))
                return False
            try:
                self.tls_requested=0
                self._make_tls_connection()
                self.socket=self.tls
            except SSLError,e:
                self.tls=0
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
        self.__logger.debug("Creating TLS context")
        if self.tls_settings.ctx:
            ctx=self.tls_settings.ctx
        else:
            ctx=SSL.Context('tlsv1')

        ctx._pyxmpp_stream=self

        if self.tls_settings.verify_peer:
            ctx.set_verify(SSL.verify_peer,10,cert_verify_callback)
        else:
            ctx.set_verify(SSL.verify_none,10)

        if self.tls_settings.cert_file:
            ctx.use_certificate_chain_file(self.tls_settings.cert_file)
            if self.tls_settings.key_file:
                ctx.use_PrivateKey_file(self.tls_settings.key_file)
            else:
                ctx.use_PrivateKey_file(self.tls_settings.cert_file)
            ctx.check_private_key()
        if self.tls_settings.cacert_file:
            ctx.load_verify_location(self.tls_settings.cacert_file)
        self.__logger.debug("Creating TLS connection")
        self.tls=SSL.Connection(ctx,self.socket)
        self.__logger.debug("Setting up TLS connection")
        self.tls.setup_ssl()
        self.__logger.debug("Setting TLS connect state")
        self.tls.set_connect_state()
        self.__logger.debug("Starting TLS handshake")
        self.tls.connect_ssl()
        self.state_change("tls connected",self.peer)
        self.tls.setblocking(0)

        # clear any exception state left by some M2Crypto broken code
        try:
            raise Exception
        except:
            pass

    def _tls_verify_callback(self,ssl_ctx_ptr, x509_ptr, errnum, depth, ok):
        """Certificate verification callback for TLS connections.
        
        :Parameters:
            - `ssl_ctx_ptr`: TLS context pointer.
            - `x509_ptr`: X.509 certificate pointer.
            - `errnum`: error number.
            - `depth`: verification depth.
            - `ok`: current verification result.
            
        :return: computed verification result."""
        try:
            self.__logger.debug("tls_verify_callback(depth=%i,ok=%i)" % (depth,ok))
            from M2Crypto.SSL.Context import map as context_map
            from M2Crypto import X509,m2
            ctx=context_map()[ssl_ctx_ptr]
            cert=X509.X509(x509_ptr)
            cb=self.tls_settings.verify_callback

            if ctx.get_verify_depth() < depth:
                self.__logger.debug(u"Certificate chain is too long (%i>%i)"
                        % (depth,ctx.get_verify_depth()))
                if cb:
                    ok=cb(self,ctx,cert,m2.X509_V_ERR_CERT_CHAIN_TOO_LONG,depth,0)
                    if not ok:
                        return 0
                else:
                    return 0

            if ok and depth==0:
                cn=cert.get_subject().CN
                if str(cn)!=str(self.peer):
                    self.__logger.debug(u"Common name does not match peer name (%s != %s)"
                            % (cn,self.peer))
                    if cb:
                        ok=cb(self,ctx,cert,TLS_ERR_BAD_CN,depth,0)
                        if not ok:
                            return 0
                    else:
                        return 0
            ok=cb(self, ctx,cert,errnum,depth,ok)
            return ok
        except:
            self.__logger.exception("Exception cought")
            raise

    def get_tls_connection(self):
        """Get the TLS connection object for the stream.

        :return: `self.tls`"""
        return self.tls

TLS_ERR_BAD_CN=1001

def cert_verify_callback(ssl_ctx_ptr, x509_ptr, errnum, depth, ok):
    """Pass control to the right verification function for a TLS connection.

    M2Crypto doesn't associate verification callbacks with connection, so
    we have one global callback, which finds and calls right callback.

    :Parameters:
        - `ssl_ctx_ptr`: TLS context pointer.
        - `x509_ptr`: X.509 certificate pointer.
        - `errnum`: error number.
        - `depth`: verification depth.
        - `ok`: current verification result.
    """
    from M2Crypto.SSL.Context import map as context_map
    ctx=context_map()[ssl_ctx_ptr]
    if hasattr(ctx,"_pyxmpp_stream"):
        stream=ctx._pyxmpp_stream
        if stream:
            return stream._tls_verify_callback(ssl_ctx_ptr,
                        x509_ptr, errnum, depth, ok)
    print >>sys.stderr,"Falling back to M2Crypto default verify callback"
    return M2Crypto.SSL.cb.ssl_verify_callback(ssl_ctx_ptr,
                        x509_ptr, errnum, depth, ok)

# vi: sts=4 et sw=4
