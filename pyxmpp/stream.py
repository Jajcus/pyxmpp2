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

"""Core XMPP stream functionality"""

__revision__="$Id: stream.py,v 1.73 2004/09/20 21:06:28 jajcus Exp $"
__docformat__="restructuredtext en"

import libxml2
import socket
import os
import sys
import time
import random
import base64
import threading
import errno
import logging


from types import StringType,UnicodeType

from pyxmpp import xmlextra
from pyxmpp.expdict import ExpiringDictionary
from pyxmpp.utils import to_utf8,remove_evil_characters
from pyxmpp.stanza import Stanza,StanzaError
from pyxmpp.error import StreamErrorNode
from pyxmpp.iq import Iq
from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.jid import JID
from pyxmpp import sasl
from pyxmpp import resolver
from pyxmpp.stanzaprocessor import StanzaProcessor

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

STREAM_NS="http://etherx.jabber.org/streams"
TLS_NS="urn:ietf:params:xml:ns:xmpp-tls"
SASL_NS="urn:ietf:params:xml:ns:xmpp-sasl"
BIND_NS="urn:ietf:params:xml:ns:xmpp-bind"

class StreamError(StandardError):
    """Base class for all stream errors."""
    pass

class StreamEncryptionRequired(StreamError):
    """Exception raised when stream encryption is requested, but not used."""
    pass

class HostMismatch(StreamError):
    """Exception raised when the connected host name is other then requested."""
    pass

class FatalStreamError(StreamError):
    """Base class for all fatal Stream exceptions.

    When `FatalStreamError` is raised the stream is no longer usable."""
    pass

class StreamParseError(FatalStreamError):
    """Raised when invalid XML is received in an XMPP stream."""
    pass

class StreamAuthenticationError(FatalStreamError):
    """Raised when stream authentication fails."""
    pass

class SASLNotAvailable(StreamAuthenticationError):
    """Raised when SASL authentication is requested, but not available."""
    pass

class SASLMechanismNotAvailable(StreamAuthenticationError):
    """Raised when none of SASL authentication mechanisms requested is
    available."""
    pass

class SASLAuthenticationFailed(StreamAuthenticationError):
    """Raised when stream SASL authentication fails."""
    pass

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

def stanza_factory(node):
    """Creates Iq, Message or Presence object for XML stanza `node`"""
    if node.name=="iq":
        return Iq(node)
    if node.name=="message":
        return Message(node)
    if node.name=="presence":
        return Presence(node)
    else:
        return Stanza(node)

class Stream(StanzaProcessor,sasl.PasswordManager,xmlextra.StreamHandler):
    """Base class for XMPP stream.
    
    Responsible for establishing connection, parsing the stream,
    StartTLS encryption and SASL authentication negotiation
    and usage, dispatching received stanzas to apopriate handlers
    and sending application's stanzas.
    
    Whenever we say "stream" here we actually mean two streams 
    (incoming and outgoing) of one connections, as defined by the XMPP
    specification.

    :Ivariables:
        - `lock`: RLock object used to synchronize access to Stream object.
        - `features`: stream features as annouced by the initiator.
        - `me`: local stream endpoint JID.
        - `peer`: remote stream endpoint JID.
        - `process_all_stanzas`: when `True` then all stanzas received are
          considered local.
        - `tls`: TLS connection object.
        - `initiator`: `True` if local stream endpoint is the initiating entity.
        - `_reader`: the stream reader object (push parser) for the stream.
    """
    def __init__(self,default_ns,extra_ns=(),sasl_mechanisms=(),
                    tls_settings=None,keepalive=0):
        """Initialize Stream object

        :Parameters:
          - `default_ns`: stream's default namespace ("jabber:client" for
            client, "jabber:server" for server, etc.)
          - `extra_ns`: sequence of extra namespace URIs to be defined for
            the stream.
          - `sasl_mechanisms`: sequence of SASL mechanisms allowed for
            authentication. Currently "PLAIN" and "DIGEST-MD5" are supported.
          - `tls_settings`: settings for StartTLS -- `TLSSettings` instance.
          - `keepalive`: keepalive output interval. 0 to disable.

        """
        StanzaProcessor.__init__(self)
        xmlextra.StreamHandler.__init__(self)
        self.default_ns_uri=default_ns
        if extra_ns:
            self.extra_ns_uris=extra_ns
        else:
            self.extra_ns_uris=[]
        if sasl_mechanisms:
            self.sasl_mechanisms=sasl_mechanisms
        else:
            self.sasl_mechanisms=[]
        self.tls_settings=tls_settings
        self.keepalive=keepalive
        self._reader_lock=threading.Lock()
        self.process_all_stanzas=False
        self.port=None
        self._reset()
        self.__logger=logging.getLogger("pyxmpp.Stream")

    def _reset(self):
        """Reset `Stream` object state making it ready to handle new
        connections."""
        self.doc_in=None
        self.doc_out=None
        self.socket=None
        self._reader=None
        self.addr=None
        self.default_ns=None
        self.peer_sasl_mechanisms=None
        self.extra_ns={}
        self.stream_ns=None
        self._reader=None
        self.ioreader=None
        self.me=None
        self.peer=None
        self.skip=False
        self.stream_id=None
        self._iq_response_handlers=ExpiringDictionary()
        self._iq_get_handlers={}
        self._iq_set_handlers={}
        self._message_handlers=[]
        self._presence_handlers=[]
        self.eof=False
        self.initiator=None
        self.features=None
        self.tls=None
        self.tls_requested=False
        self.authenticator=None
        self.authenticated=False
        self.peer_authenticated=False
        self.auth_method_used=None
        self.version=None
        self.last_keepalive=False

    def __del__(self):
        self.close()

    def _connect_socket(self,sock,to=None):
        """Initialize stream on outgoing connection.

        :Parameters:
          - `sock`: connected socket for the stream
          - `to`: name of the remote host
        """
        self.eof=0
        self.socket=sock
        if to:
            self.peer=JID(to)
        else:
            self.peer=None
        self.initiator=1
        self._send_stream_start()
        self._make_reader()

    def connect(self,addr,port,service=None,to=None):
        """Establish XMPP connection with given address.

        [initiating entity only]
        
        :Parameters:
            - `addr`: peer name or IP address
            - `port`: port number to connect to
            - `service`: service name (to be resolved using SRV DNS records)
            - `to`: peer name if different than `addr`
        """
        self.lock.acquire()
        try:
            return self._connect(addr,port,service,to)
        finally:
            self.lock.release()

    def _connect(self,addr,port,service=None,to=None):
        """Same as `Stream.connect` but assume `self.lock` is acquired."""
        if to is None:
            to=str(addr)
        if service is not None:
            self.state_change("resolving srv",(addr,service))
            addrs=resolver.resolve_srv(addr,service)
            if not addrs:
                addrs=[(addr,port)]
        else:
            addrs=[(addr,port)]
        msg=None
        for addr,port in addrs:
            if type(addr) in (StringType,UnicodeType):
                self.state_change("resolving",addr)
            s=None
            for res in resolver.getaddrinfo(addr,port,0,socket.SOCK_STREAM):
                family,socktype,proto,canonname,sockaddr=res
                try:
                    s=socket.socket(family,socktype,proto)
                    self.state_change("connecting",sockaddr)
                    s.connect(sockaddr)
                    self.state_change("connected",sockaddr)
                except socket.error, msg:
                    self.__logger.debug("Connect to %r failed" % (sockaddr,))
                    if s:
                        s.close()
                        s=None
                    continue
                break
            if s:
                break
        if not s:
            if msg:
                raise socket.error, msg
            else:
                raise FatalStreamError,"Cannot connect"

        self.addr=addr
        self.port=port
        self._connect_socket(s,to)
        self.last_keepalive=time.time()

    def accept(self,sock,myname):
        """Accept incoming connection.

        [receiving entity only]

        :Parameters:
            - `sock`: a listening socket.
            - `myname`: local stream endpoint name."""
        self.lock.acquire()
        try:
            return self._accept(sock,myname)
        finally:
            self.lock.release()

    def _accept(self,sock,myname):
        """Same as `Stream.accept` but assume `self.lock` is acquired."""
        self.eof=0
        self.socket,addr=sock.accept()
        self.__logger.debug("Connection from: %r" % (addr,))
        self.addr,self.port=addr
        if myname:
            self.me=JID(myname)
        else:
            self.me=None
        self.initiator=0
        self._make_reader()
        self.last_keepalive=time.time()

    def disconnect(self):
        """Gracefully close the connection."""
        self.lock.acquire()
        try:
            return self._disconnect()
        finally:
            self.lock.release()

    def _disconnect(self):
        """Same as `Stream.disconnect` but assume `self.lock` is acquired."""
        if self.doc_out:
            self._send_stream_end()

    def _post_connect(self):
        """Called when connection is established.

        This method is supposed to be overriden in derived classes."""
        pass

    def _post_auth(self):
        """Called when connection is authenticated.

        This method is supposed to be overriden in derived classes."""
        pass

    def state_change(self,state,arg):
        """Called when connection state is changed.

        This method is supposed to be overriden in derived classes
        or replaced by an application.
        
        It may be used to display the connection progress."""
        self.__logger.debug("State: %s: %r" % (state,arg))

    def close(self):
        """Forcibly close the connection and clear the stream state."""
        self.lock.acquire()
        try:
            return self._close()
        finally:
            self.lock.release()

    def _close(self):
        """Same as `Stream.close` but assume `self.lock` is acquired."""
        self._disconnect()
        if self.doc_in:
            self.doc_in=None
        if self.features:
            self.features=None
        self._reader=None
        self.stream_id=None
        if self.socket:
            self.socket.close()
        self._reset()

    def _make_reader(self):
        """Create ne `xmlextra.StreamReader` instace as `self._reader`."""
        self._reader=xmlextra.StreamReader(self)

    def stream_start(self,doc):
        """Process <stream:stream> (stream start) tag received from peer.
        
        :Parameters:
            - `doc`: document created by the parser"""
        self.doc_in=doc
        self.__logger.debug("input document: %r" % (self.doc_in.serialize(),))

        try:
            r=self.doc_in.getRootElement()
            if r.ns().getContent() != STREAM_NS:
                self._send_stream_error("invalid-namespace")
                raise FatalStreamError,"Invalid namespace."
        except libxml2.treeError:
            self._send_stream_error("invalid-namespace")
            raise FatalStreamError,"Couldn't get the namespace."

        self.version=r.prop("version")
        if self.version and self.version!="1.0":
            self._send_stream_error("unsupported-version")
            raise FatalStreamError,"Unsupported protocol version."

        to_from_mismatch=0
        if self.initiator:
            self.stream_id=r.prop("id")
            peer=r.prop("from")
            if peer:
                peer=JID(peer)
            if self.peer:
                if peer and peer!=self.peer:
                    self.__logger.debug("peer hostname mismatch:"
                        " %r != %r" % (peer,self.peer))
                    to_from_mismatch=1
            else:
                self.peer=peer
        else:
            to=r.prop("to")
            if to:
                to=self.check_to(to)
                if not to:
                    self._send_stream_error("host-unknown")
                    raise FatalStreamError,'Bad "to"'
                self.me=JID(to)
            self._send_stream_start(self.generate_id())
            self._send_stream_features()
            self.state_change("fully connected",self.peer)
            self._post_connect()

        if not self.version:
            self.state_change("fully connected",self.peer)
            self._post_connect()

        if to_from_mismatch:
            raise HostMismatch

    def stream_end(self,doc):
        """Process </stream:stream> (stream end) tag received from peer.
        
        :Parameters:
            - `doc`: document created by the parser"""
        self.__logger.debug("Stream ended")
        self.eof=1
        if self.doc_out:
            self._send_stream_end()
        if self.doc_in:
            self.doc_in=None
            self._reader=None
            if self.features:
                self.features=None
        self.state_change("disconnected",self.peer)

    def stanza_start(self,doc,node):
        """Process stanza (first level child element of the stream) start tag
        -- do nothing.
        
        :Parameters:
            - `doc`: parsed document
            - `node`: stanza's full XML
        """
        pass

    def stanza_end(self,doc,node):
        """Process stanza (first level child element of the stream) end tag.
        
        :Parameters:
            - `doc`: parsed document
            - `node`: stanza's full XML
        """
        self._process_node(node)

    def stanza(self,doc,node):
        """Process stanza (first level child element of the stream).
        
        :Parameters:
            - `doc`: parsed document
            - `node`: stanza's full XML
        """
        self._process_node(node)

    def error(self,descr):
        """Handle stream XML parse error.
        
        :Parameters:
            - `descr`: error description
        """
        raise StreamParseError,descr

    def _send_stream_end(self):
        """Send stream end tag."""
        self.doc_out.getRootElement().addContent(" ")
        s=self.doc_out.getRootElement().serialize(encoding="UTF-8")
        end=s.rindex("<")
        try:
            self._write_raw(s[end:])
        except (IOError,SystemError,socket.error),e:
            self.__logger.debug("Sending stream closing tag failed:"+str(e))
        self.doc_out.freeDoc()
        self.doc_out=None
        if self.features:
            self.features=None

    def _send_stream_start(self,sid=None):
        """Send stream start tag."""
        if self.doc_out:
            raise StreamError,"Stream start already sent"
        self.doc_out=libxml2.newDoc("1.0")
        root=self.doc_out.newChild(None, "stream", None)
        self.stream_ns=root.newNs(STREAM_NS,"stream")
        root.setNs(self.stream_ns)
        self.default_ns=root.newNs(self.default_ns_uri,None)
        for prefix,uri in self.extra_ns:
            self.extra_ns[uri]=root.newNs(uri,prefix)
        if self.peer:
            root.setProp("to",self.peer.as_utf8())
        if self.me:
            root.setProp("from",self.me.as_utf8())
        root.setProp("version","1.0")
        if sid:
            root.setProp("id",sid)
            self.stream_id=sid
        sr=self.doc_out.serialize(encoding="UTF-8")
        self._write_raw(sr[:sr.find("/>")]+">")

    def _send_stream_error(self,condition):
        """Send stream error element.
        
        :Parameters:
            - `condition`: stream error condition name, as defined in the
              XMPP specification."""
        if not self.doc_out:
            self._send_stream_start()
        e=StreamErrorNode(condition)
        e.node.setNs(self.stream_ns)
        self._write_raw(e.serialize())
        e.free()
        self._send_stream_end()

    def _restart_stream(self):
        """Restart the stream as needed after SASL and StartTLS negotiation."""
        self._reader=None
        #self.doc_out.freeDoc()
        self.doc_out=None
        #self.doc_in.freeDoc() # memleak, but the node which caused the restart
                    # will be freed after this function returns
        self.doc_in=None
        self.features=None
        if self.initiator:
            self._send_stream_start(self.stream_id)
        self._make_reader()

    def _make_stream_features(self):
        """Create the <features/> element for the stream.

        [receving entity only]
        
        :returns: new <features/> element node."""
        root=self.doc_out.getRootElement()
        features=root.newChild(root.ns(),"features",None)
        if self.sasl_mechanisms and not self.authenticated:
            ml=features.newChild(None,"mechanisms",None)
            ns=ml.newNs(SASL_NS,None)
            ml.setNs(ns)
            for m in self.sasl_mechanisms:
                if m in sasl.all_mechanisms:
                    ml.newTextChild(ns,"mechanism",m)
        if self.tls_settings and not self.tls:
            tls=features.newChild(None,"starttls",None)
            ns=tls.newNs(TLS_NS,None)
            tls.setNs(ns)
            if self.tls_settings.require:
                tls.newChild(ns,"required",None)
        return features

    def _send_stream_features(self):
        """Send stream <features/>.
        
        [receiving entity only]"""
        self.features=self._make_stream_features()
        self._write_raw(self.features.serialize(encoding="UTF-8"))

    def write_raw(self,data):
        """Write raw data to the stream socket.
        
        :Parameters:
            - `data`: data to send"""
        self.lock.acquire()
        try:
            return self._write_raw(data)
        finally:
            self.lock.release()

    def _write_raw(self,data):
        """Same as `Stream.write_raw` but assume `self.lock` is acquired."""
        logging.getLogger("pyxmpp.Stream.out").debug("OUT: %r",data)
        try:
            self.socket.send(data)
        except (IOError,OSError),e:
            raise FatalStreamError("IO Error: "+str(e))
        except SSLError,e:
            raise TLSError("TLS Error: "+str(e))

    def _write_node(self,node):
        """Write XML `node` to the stream.
        
        :Parameters:
            - `node`: XML node to send."""
        if self.eof or not self.socket or not self.doc_out:
            self.__logger.debug("Dropping stanza: %r" % (node,))
            return
        node=node.docCopyNode(self.doc_out,1)
        self.doc_out.addChild(node)
        #node.reconciliateNs(self.doc_out)
        s=node.serialize(encoding="UTF-8")
        s=remove_evil_characters(s)
        self._write_raw(s)
        node.unlinkNode()
        node.freeNode()

    def send(self,stanza):
        """Write stanza to the stream.
        
        :Parameters:
            - `stanza`: XMPP stanza to send."""
        self.lock.acquire()
        try:
            return self._send(stanza)
        finally:
            self.lock.release()

    def _send(self,stanza):
        """Same as `Stream.send` but assume `self.lock` is acquired."""
        if self.tls_settings and self.tls_settings.require and not self.tls:
            raise StreamEncryptionRequired,"TLS encryption required and not started yet"

        if not self.version:
            try:
                err=stanza.get_error()
            except StanzaError:
                err=None
            if err:
                err.downgrade()
        self.fix_out_stanza(stanza)
        self._write_node(stanza.node)

    def idle(self):
        """Do some housekeeping (cache expiration, timeout handling).
        
        This method should be called periodically from the application's
        main loop."""
        self.lock.acquire()
        try:
            return self._idle()
        finally:
            self.lock.release()

    def _idle(self):
        """Same as `Stream.idle` but assume `self.lock` is acquired."""
        self._iq_response_handlers.expire()
        if not self.socket or self.eof:
            return
        now=time.time()
        if self.keepalive and now-self.last_keepalive>=self.keepalive:
            self._write_raw(" ")
            self.last_keepalive=now

    def fileno(self):
        """Return filedescriptor of the stream socket."""
        self.lock.acquire()
        try:
            return self.socket.fileno()
        finally:
            self.lock.release()

    def loop(self,timeout):
        """Simple "main loop" for the stream."""
        self.lock.acquire()
        try:
            while not self.eof and self.socket is not None:
                act=self._loop_iter(timeout)
                if not act:
                    self._idle()
        finally:
            self.lock.release()

    def loop_iter(self,timeout):
        """Single iteration of a simple "main loop" for the stream."""
        self.lock.acquire()
        try:
            return self._loop_iter(timeout)
        finally:
            self.lock.release()

    def _loop_iter(self,timeout):
        """Same as `Stream.loop_iter` but assume `self.lock` is acquired."""
        import select
        self.lock.release()
        try:
            try:
                ifd,ofd,efd=select.select([self.socket],[],[self.socket],timeout)
            except select.error,e:
                if e.args[0]!=errno.EINTR:
                    raise
                ifd,ofd,efd=[],[],[]
        finally:
            self.lock.acquire()
        if self.socket in ifd or self.socket in efd:
            self._process()
            return True
        else:
            return False

    def process(self):
        """Process stream's pending events.

        Should be called whenever there is input available
        on `self.fileno()` socket descriptor. Is called by
        `self.loop_iter`."""
        self.lock.acquire()
        try:
            self._process()
        finally:
            self.lock.release()

    def _process(self):
        """Same as `Stream.process` but assume `self.lock` is acquired."""
        try:
            self._read()
        except SSLError,e:
            self.close()
            raise TLSError("TLS Error: "+str(e))
        except (IOError,OSError),e:
            self.close()
            raise FatalStreamError("IO Error: "+str(e))
        except (FatalStreamError,KeyboardInterrupt,SystemExit),e:
            self.close()
            raise

    def _read(self):
        """Read data pending on the stream socket and pass it to the parser."""
        if self.eof:
            return
        try:
            if not self.tls:
                r=os.read(self.socket.fileno(),1024)
            else:
                r=self.socket.read()
                if r is None:
                    return
        except socket.error,e:
            if e.args[0]!=errno.EINTR:
                raise
            return
        logging.getLogger("pyxmpp.Stream.in").debug("IN: %r",r)
        if r:
            try:
                r=self._reader.feed(r)
                while r:
                    r=self._reader.feed("")
                if r is None:
                    self.eof=1
                    self.disconnect()
            except StreamParseError:
                self._send_stream_error("xml-not-well-formed")
                raise
        else:
            self.eof=1
            self.disconnect()
        if self.eof:
            self.stream_end(None)

    def _process_node(self,node):
        """Process first level element of the stream.

        The element may be stream error or features, StartTLS
        request/response, SASL request/response or a stanza.

        :Parameters:
            - `node`: XML node describing the element
        """
        ns_uri=node.ns().getContent()
        if ns_uri=="http://etherx.jabber.org/streams":
            self._process_stream_node(node)
            return
        elif ns_uri==TLS_NS:
            self._process_tls_node(node)
            return

        if self.tls_settings and self.tls_settings.require and not self.tls:
            raise StreamEncryptionRequired,"TLS encryption required and not started yet"

        if ns_uri==self.default_ns_uri:
            stanza=stanza_factory(node)
            self.lock.release()
            try:
                self.process_stanza(stanza)
            finally:
                self.lock.acquire()
                stanza.free()
        elif ns_uri==SASL_NS:
            self._process_sasl_node(node)
        else:
            self.__logger.debug("Unhandled node: %r" % (node.serialize(),))

    def _process_stream_node(self,node):
        """Process first level stream-namespaced element of the stream.

        The element may be stream error or stream features.

        :Parameters:
            - `node`: XML node describing the element
        """
        if node.name=="error":
            e=StreamErrorNode(node)
            self.lock.release()
            try:
                self.process_stream_error(e)
            finally:
                self.lock.acquire()
                e.free()
            return
        elif node.name=="features":
            self.__logger.debug("Got stream features")
            self.__logger.debug("Node: %r" % (node,))
            self.features=node.copyNode(1)
            self.doc_in.addChild(self.features)
            self._got_features()
            return

        if self.tls_settings and self.tls_settings.require and not self.tls:
            raise StreamEncryptionRequired,"TLS encryption required and not started yet"

        self.__logger.debug("Unhandled stream node: %r" % (node.serialize(),))

    def process_stream_error(self,err):
        """Process stream error element received.

        :Types:
            - `err`: `StreamErrorNode`

        :Parameters:
            - `err`: error received
        """

        self.__logger.debug("Unhandled stream error: condition: %s %r"
                % (err.get_condition().name,err.serialize()))

    def check_to(self,to):
        """Check "to" attribute of received stream header.

        :return: `to` if it is equal to `self.me`, None otherwise.

        Should be overriden in derived classes which require other logic
        for handling that attribute."""
        if to!=self.me:
            return None
        return to

    def generate_id(self):
        """Generate a random and unique stream ID.
        
        :return: the id string generated."""
        return "%i-%i-%s" % (os.getpid(),time.time(),str(random.random())[2:])

    def _got_features(self):
        """Process incoming <stream:features/> element.

        [initiating entity only]

        The received features node is available in `self.features`."""
        ctxt = self.doc_in.xpathNewContext()
        ctxt.setContextNode(self.features)
        ctxt.xpathRegisterNs("stream",STREAM_NS)
        ctxt.xpathRegisterNs("tls",TLS_NS)
        ctxt.xpathRegisterNs("sasl",SASL_NS)
        ctxt.xpathRegisterNs("bind",BIND_NS)
        try:
            tls_n=ctxt.xpathEval("tls:starttls")
            tls_required_n=ctxt.xpathEval("tls:starttls/tls:required")
            sasl_mechanisms_n=ctxt.xpathEval("sasl:mechanisms/sasl:mechanism")
            bind_n=ctxt.xpathEval("bind:bind")
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
        if sasl_mechanisms_n:
            self.__logger.debug("SASL support found")
            self.peer_sasl_mechanisms=[]
            for n in sasl_mechanisms_n:
                self.peer_sasl_mechanisms.append(n.getContent())
        if not self.tls_requested and not self.authenticated:
            self.state_change("fully connected",self.peer)
            self._post_connect()

        if self.authenticated:
            if bind_n:
                self.bind(self.me.resource)
            else:
                self.state_change("authorized",self.me)

    def bind(self,resource):
        """Bind to a resource.

        [initiating entity only]
        
        :Parameters:
            - `resource`: the resource name to bind to.
        
        XMPP stream is authenticated for bare JID only. To use
        the full JID it must be bound to a resource.
        """
        iq=Iq(stanza_type="set")
        q=iq.new_query(BIND_NS,"bind")
        if resource:
            q.newTextChild(q.ns(),"resource",to_utf8(resource))
        self.state_change("binding",resource)
        self.set_response_handlers(iq,self._bind_success,self._bind_error)
        self.send(iq)
        iq.free()

    def _bind_success(self,stanza):
        """Handle resource binding success.

        [initiating entity only]

        :Parameters:
            - `stanza`: <iq type="result"/> stanza received.
        
        Set `self.me` to the full JID negotiated."""
        jid_n=stanza.xpath_eval("bind:bind/bind:jid",{"bind":BIND_NS})
        if jid_n:
            self.me=JID(jid_n[0].getContent())
        self.state_change("authorized",self.me)

    def _bind_error(self,stanza):
        """Handle resource binding success.

        [initiating entity only]

        :raise FatalStreamError:"""
        raise FatalStreamError,"Resource binding failed"

    def connected(self):
        """Check if stream is connected.

        :return: True if stream connection is active."""
        if self.doc_in and self.doc_out and not self.eof:
            return True
        else:
            return False

    def _process_sasl_node(self,node):
        """Process stream element in the SASL namespace.
        
        :Parameters:
            - `node`: the XML node received
        """
        if self.initiator:
            if not self.authenticator:
                self.__logger.debug("Unexpected SASL response: %r" % (node.serialize()))
                return False
            if node.name=="challenge":
                return self._process_sasl_challenge(node.getContent())
            if node.name=="success":
                return self._process_sasl_success(node.getContent())
            if node.name=="failure":
                return self._process_sasl_failure(node)
            self.__logger.debug("Unexpected SASL node: %r" % (node.serialize()))
            return False
        else:
            if node.name=="auth":
                mechanism=node.prop("mechanism")
                return self._process_sasl_auth(mechanism,node.getContent())
            if node.name=="response":
                return self._process_sasl_response(node.getContent())
            if node.name=="abort":
                return self._process_sasl_abort()
            self.__logger.debug("Unexpected SASL node: %r" % (node.serialize()))
            return False

    def _process_sasl_auth(self,mechanism,content):
        """Process incoming <sasl:auth/> element.

        [receiving entity only]

        :Parameters:
            - `mechanism`: mechanism choosen by the peer.
            - `content`: optional "initial response" included in the element.
        """
        if self.authenticator:
            self.__logger.debug("Authentication already started")
            return False

        self.auth_method_used="sasl:"+mechanism
        self.authenticator=sasl.ServerAuthenticator(mechanism,self)

        r=self.authenticator.start(base64.decodestring(content))

        if isinstance(r,sasl.Success):
            el_name="success"
            content=r.base64()
        elif isinstance(r,sasl.Challenge):
            el_name="challenge"
            content=r.base64()
        else:
            el_name="failure"
            content=None

        root=self.doc_out.getRootElement()
        node=root.newChild(None,el_name,None)
        ns=node.newNs(SASL_NS,None)
        node.setNs(ns)
        if content:
            node.setContent(content)
        if isinstance(r,sasl.Failure):
            node.newChild(ns,r.reason,None)

        self._write_raw(node.serialize(encoding="UTF-8"))
        node.unlinkNode()
        node.freeNode()

        if isinstance(r,sasl.Success):
            if r.authzid:
                self.peer=JID(r.authzid)
            else:
                self.peer=JID(r.username,self.me.domain)
            self.peer_authenticated=1
            self.state_change("authenticated",self.peer)
            self._post_auth()

        if isinstance(r,sasl.Failure):
            raise SASLAuthenticationFailed,"SASL authentication failed"

        return True

    def _process_sasl_challenge(self,content):
        """Process incoming <sasl:challenge/> element.

        [initiating entity only]

        :Parameters:
            - `content`: the challenge data received (Base64-encoded).
        """
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL challenge")
            return False

        r=self.authenticator.challenge(base64.decodestring(content))
        if isinstance(r,sasl.Response):
            el_name="response"
            content=r.base64()
        else:
            el_name="abort"
            content=None

        root=self.doc_out.getRootElement()
        node=root.newChild(None,el_name,None)
        ns=node.newNs(SASL_NS,None)
        node.setNs(ns)
        if content:
            node.setContent(content)

        self._write_raw(node.serialize(encoding="UTF-8"))
        node.unlinkNode()
        node.freeNode()

        if isinstance(r,sasl.Failure):
            raise SASLAuthenticationFailed,"SASL authentication failed"

        return True

    def _process_sasl_response(self,content):
        """Process incoming <sasl:response/> element.

        [receiving entity only]

        :Parameters:
            - `content`: the response data received (Base64-encoded).
        """
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL response")
            return 0

        r=self.authenticator.response(base64.decodestring(content))
        if isinstance(r,sasl.Success):
            el_name="success"
            content=r.base64()
        elif isinstance(r,sasl.Challenge):
            el_name="challenge"
            content=r.base64()
        else:
            el_name="failure"
            content=None

        root=self.doc_out.getRootElement()
        node=root.newChild(None,el_name,None)
        ns=node.newNs(SASL_NS,None)
        node.setNs(ns)
        if content:
            node.setContent(content)
        if isinstance(r,sasl.Failure):
            node.newChild(ns,r.reason,None)

        self._write_raw(node.serialize(encoding="UTF-8"))
        node.unlinkNode()
        node.freeNode()

        if isinstance(r,sasl.Success):
            authzid=r.authzid
            if authzid:
                self.peer=JID(r.authzid)
            else:
                self.peer=JID(r.username,self.me.domain)
            self.peer_authenticated=1
            self._restart_stream()
            self.state_change("authenticated",self.peer)
            self._post_auth()

        if isinstance(r,sasl.Failure):
            raise SASLAuthenticationFailed,"SASL authentication failed"

        return 1

    def _process_sasl_success(self,content):
        """Process incoming <sasl:success/> element.

        [initiating entity only]

        :Parameters:
            - `content`: the "additional data with success" received (Base64-encoded).
        """
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL response")
            return False

        r=self.authenticator.finish(base64.decodestring(content))
        if isinstance(r,sasl.Success):
            self.__logger.debug("SASL authentication succeeded")
            if r.authzid:
                self.me=JID(r.authzid)
            else:
                self.me=self.me
            self.authenticated=1
            self._restart_stream()
            self.state_change("authenticated",self.me)
            self._post_auth()
        else:
            self.__logger.debug("SASL authentication failed")
            raise SASLAuthenticationFailed,"Additional success data procesing failed"
        return True

    def _process_sasl_failure(self,node):
        """Process incoming <sasl:failure/> element.

        [initiating entity only]

        :Parameters:
            - `node`: the XML node received.
        """
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL response")
            return False

        self.__logger.debug("SASL authentication failed: %r" % (node.serialize(),))
        raise SASLAuthenticationFailed,"SASL authentication failed"

    def _process_sasl_abort(self):
        """Process incoming <sasl:abort/> element.

        [receiving entity only]"""
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL response")
            return False

        self.authenticator=None
        self.__logger.debug("SASL authentication aborted")
        return True

    def _sasl_authenticate(self,username,authzid,mechanism=None):
        """Start SASL authentication process.

        [initiating entity only]
        
        :Parameters:
            - `username`: user name.
            - `authzid`: authorization ID.
            - `mechanism`: SASL mechanism to use."""
        if not self.initiator:
            raise SASLAuthenticationFailed,"Only initiating entity start SASL authentication"
        while not self.features:
            self.__logger.debug("Waiting for features")
            self._read()
        if not self.peer_sasl_mechanisms:
            raise SASLNotAvailable,"Peer doesn't support SASL"

        if not mechanism:
            mechanism=None
            for m in self.sasl_mechanisms:
                if m in self.peer_sasl_mechanisms:
                    mechanism=m
                    break
            if not mechanism:
                raise SASLMechanismNotAvailable,"Peer doesn't support any of our SASL mechanisms"
            self.__logger.debug("Our mechanism: %r" % (mechanism,))
        else:
            if mechanism not in self.peer_sasl_mechanisms:
                raise SASLMechanismNotAvailable,"%s is not available" % (mechanism,)

        self.auth_method_used="sasl:"+mechanism

        self.authenticator=sasl.ClientAuthenticator(mechanism,self)

        initial_response=self.authenticator.start(username,authzid)
        if not isinstance(initial_response,sasl.Response):
            raise SASLAuthenticationFailed,"SASL initiation failed"

        root=self.doc_out.getRootElement()
        node=root.newChild(None,"auth",None)
        ns=node.newNs(SASL_NS,None)
        node.setNs(ns)
        node.setProp("mechanism",mechanism)
        if initial_response.data:
            node.setContent(initial_response.base64())

        self._write_raw(node.serialize(encoding="UTF-8"))
        node.unlinkNode()
        node.freeNode()

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
