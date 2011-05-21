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

"""Core XMPP stream functionality.

Normative reference:
  - `RFC 6120 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import socket
import time
import errno
import logging
import uuid
import re

from xml.etree import ElementTree


from .xmppparser import StreamHandler
from .expdict import ExpiringDictionary
from .error import StreamErrorElement
from .iq import Iq
from .jid import JID
from . import resolver
from .stanzaprocessor import StanzaProcessor, stanza_factory
from .exceptions import StreamError, BadRequestProtocolError
from .exceptions import HostMismatch
from .exceptions import DNSError, UnexpectedCNAMEError
from .exceptions import FatalStreamError, StreamParseError
from .constants import STREAM_QNP, BIND_QNP, XML_LANG_QNAME
from .settings import XMPPSettings
from .xmppserializer import serialize, XMPPSerializer
from .xmppparser import StreamReader
from .stanzapayload import XMLPayload

from .streamevents import AuthorizedEvent, BindingResourceEvent, ConnectedEvent
from .streamevents import ConnectingEvent, ConnectionAcceptedEvent
from .streamevents import DisconnectedEvent, ResolvingAddressEvent
from .streamevents import ResolvingSRVEvent, StreamConnectedEvent

XMPPSettings.add_defaults(
        {
            u"language": "en",
            u"languages": ("en",),
            u"keepalive": 0,
            u"default_stanza_timeout": 300,
            u"extra_ns_prefixes": {},
        })

logger = logging.getLogger("pyxmpp.streambase")

LANG_SPLIT_RE = re.compile(r"(.*)(?:-[a-zA-Z0-9])?-[a-zA-Z0-9]+$")

ERROR_TAG = STREAM_QNP + u"error"
FEATURES_TAG = STREAM_QNP + u"features"
FEATURE_BIND = BIND_QNP + u"bind"

class StreamBase(StanzaProcessor, StreamHandler):
    """Base class for a generic XMPP stream.

    Responsible for establishing connection, parsing the stream, dispatching
    received stanzas to apopriate handlers and sending application's stanzas.
    This doesn't provide any authentication or encryption (both required by
    the XMPP specification) and is not usable on its own.

    Whenever we say "stream" here we actually mean two streams
    (incoming and outgoing) of one connections, as defined by the XMPP
    specification.

    :Ivariables:
        - `stanza_namespace`: default namespace of the stream
        - `settings`: stream settings
        - `lock`: RLock object used to synchronize access to Stream object.
        - `features`: stream features as annouced by the initiator.
        - `me`: local stream endpoint JID.
        - `peer`: remote stream endpoint JID.
        - `process_all_stanzas`: when `True` then all stanzas received are
          considered local.
        - `initiator`: `True` if local stream endpoint is the initiating entity.
        - `_reader`: the stream reader object (push parser) for the stream.
        - `version`: Negotiated version of the XMPP protocol. (0,9) for the
          legacy (pre-XMPP) Jabber protocol.
    :Types:
        - `settings`: XMPPSettings
        - `version`: (`int`, `int`) tuple
    """
    def __init__(self, stanza_namespace, settings = None):
        """Initialize Stream object

        :Parameters:
          - `stanza_namespace`: stream's default namespace URI ("jabber:client"
            for client, "jabber:server" for server, etc.)
          - `settings`: extra settings
        :Types:
          - `stanza_namespace`: `unicode`
          - `settings`: XMPPSettings
        """
        StreamHandler.__init__(self)
        if settings is None:
            settings = XMPPSettings()
        self.settings = settings
        StanzaProcessor.__init__(self, settings[u"default_stanza_timeout"])
        self.stanza_namespace = stanza_namespace
        self._stanza_namespace_p = "{{{0}}}".format(stanza_namespace)
        self.keepalive = self.settings[u"keepalive"]
        self.process_all_stanzas = False
        self.port = None
        self._reset()

    def _reset(self):
        """Reset `Stream` object state making it ready to handle new
        connections."""
        self.socket = None
        self._reader = None
        self.addr = None
        self.me = None
        self.peer = None
        self.stream_id = None
        self.eof = False
        self.initiator = None
        self.features = None
        self.authenticated = False
        self.peer_authenticated = False
        self.auth_method_used = None
        self.version = None
        self.last_keepalive = False
        self.language = None
        self.peer_language = None
        self._serializer = None

        # FIXME?
        self._iq_response_handlers = ExpiringDictionary()
        self._iq_get_handlers = {}
        self._iq_set_handlers = {}
        self._message_handlers = []
        self._presence_handlers = []

    def _connect_socket(self, sock, to = None):
        """Initialize stream on outgoing connection.

        :Parameters:
          - `sock`: connected socket for the stream
          - `to`: name of the remote host
        """
        self.eof = False
        self.socket = sock
        if to:
            self.peer = JID(to)
        else:
            self.peer = None
        self.initiator = True
        self._send_stream_start()
        self._make_reader()

    def connect(self, addr, port, service = None, to = None):
        """Establish XMPP connection with given address.

        [initiating entity only]

        :Parameters:
            - `addr`: peer name or IP address
            - `port`: port number to connect to
            - `service`: service name (to be resolved using SRV DNS records)
            - `to`: peer name if different than `addr`
        """
        with self.lock:
            return self._connect(addr, port, service, to)

    def _connect(self, addr, port, service = None, to = None):
        """Same as `Stream.connect` but assume `self.lock` is acquired."""
        if to is None:
            to = unicode(addr)
        allow_cname = True
        if service is not None:
            self.event(ResolvingSRVEvent(addr, service))
            addrs = resolver.resolve_srv(addr, service)
            if not addrs:
                addrs = [(addr, port)]
            else:
                allow_cname = False
        else:
            addrs = [(addr, port)]
        exception = None
        for addr, port in addrs:
            if type(addr) in (str, unicode):
                self.event(ResolvingAddressEvent(addr))
            sock = None
            while True:
                try:
                    addresses = resolver.getaddrinfo(addr, port, None,
                                socket.SOCK_STREAM, allow_cname = allow_cname)
                    break
                except UnexpectedCNAMEError, err:
                    logger.warning(str(err))
                    allow_cname = True
                    continue
                except DNSError, err:
                    logger.debug(str(err))
                    exception = err
                    addresses = []
                    break
            for res in addresses:
                family, socktype, proto, _unused, sockaddr = res
                try:
                    sock = socket.socket(family, socktype, proto)
                    self.event(ConnectingEvent(sockaddr))
                    sock.connect(sockaddr)
                    self.event(ConnectedEvent(sockaddr))
                except socket.error, err:
                    exception = err
                    logger.debug("Connect to {0!r} failed".format(sockaddr))
                    if sock:
                        sock.close()
                        sock = None
                    continue
                break
            if sock:
                break
        if not sock:
            if exception:
                raise exception # pylint: disable-msg=E0702
            else:
                raise FatalStreamError("Cannot connect")

        self.addr = addr
        self.port = port
        self._connect_socket(sock, to)
        self.last_keepalive = time.time()

    def accept(self, sock, myname):
        """Accept incoming connection.

        [receiving entity only]

        :Parameters:
            - `sock`: a listening socket.
            - `myname`: local stream endpoint name."""
        with self.lock:
            return self._accept(sock, myname)

    def _accept(self, sock, myname):
        """Same as `Stream.accept` but assume `self.lock` is acquired."""
        self.eof = False
        self.socket, addr = sock.accept()
        self.event(ConnectionAcceptedEvent(addr))
        logger.debug("Connection from: %r" % (addr,))
        self.addr, self.port = addr
        if myname:
            self.me = JID(myname)
        else:
            self.me = None
        self.initiator = 0
        self._make_reader()
        self.last_keepalive = time.time()

    def disconnect(self):
        """Gracefully close the connection."""
        with self.lock:
            return self._disconnect()

    def _disconnect(self):
        """Same as `Stream.disconnect` but assume `self.lock` is acquired."""
        if self._serializer:
            self._send_stream_end()

    def _post_connect(self):
        """Called when connection is established.

        This method is supposed to be overriden in derived classes."""
        pass

    def _post_auth(self):
        """Called when connection is authenticated.

        This method is supposed to be overriden in derived classes."""
        pass

    def event(self, event): # pylint: disable-msg=R0201
        """Handle a stream event.
        
        Called when connection state is changed.

        This method is supposed to be overriden in derived classes.

        It may be used to display the connection progress."""
        logger.debug(u"Stream event: {0}".format(event))

    def close(self):
        """Forcibly close the connection and clear the stream state."""
        with self.lock:
            return self._close()

    def _close(self):
        """Same as `Stream.close` but assume `self.lock` is acquired."""
        self._disconnect()
        if self.socket:
            self.socket.close()
        self._reset()

    def _make_reader(self):
        """Create ne `StreamReader` instace as `self._reader`."""
        self._reader = StreamReader(self)

    def stream_start(self, element):
        """Process <stream:stream> (stream start) tag received from peer.

        :Parameters:
            - `element`: root element (empty) created by the parser"""
        logger.debug("input document: " + ElementTree.dump(element))
        if not element.tag.starts_with(STREAM_QNP):
            self._send_stream_error("invalid-namespace")
            raise FatalStreamError("Bad stream namespace")

        version = element.get("version")
        if version:
            try:
                major, minor = version.split(".", 1)
            except ValueError:
                self._send_stream_error("unsupported-version")
                raise FatalStreamError("Unsupported protocol version.")
            self.version = (major, minor)
        else:
            self.version = (0, 9)

        if self.version[0] != 1 and self.version != (0, 9):
            self._send_stream_error("unsupported-version")
            raise FatalStreamError("Unsupported protocol version.")

        peer_lang = element.get(XML_LANG_QNAME)
        self.peer_language = peer_lang
        if not self.initiator:
            lang = None
            languages = self.settings["languages"]
            while peer_lang:
                if peer_lang in languages:
                    lang = peer_lang
                    break
                match = LANG_SPLIT_RE.match(peer_lang)
                if not match:
                    break
                peer_lang = match.group(0)
            if lang:
                self.language = lang

        to_from_mismatch = False
        if self.initiator:
            self.stream_id = element.get("id")
            peer = element.get("from")
            if peer:
                peer = JID(peer)
            if self.peer:
                if peer and peer != self.peer:
                    logger.debug("peer hostname mismatch: {0!r} != {1!r}"
                                                    .format(peer,self.peer))
                    to_from_mismatch = True
            else:
                self.peer = peer
        else:
            to = element.get("to")
            if to:
                to = self.check_to(to)
                if not to:
                    self._send_stream_error("host-unknown")
                    raise FatalStreamError('Bad "to"')
                self.me = JID(to)
            self._send_stream_start(self.generate_id())
            self._send_stream_features()
            self.event(StreamConnectedEvent(self.peer))
            self._post_connect()

        if self.version == (0, 9):
            self.event(StreamConnectedEvent(self.peer))
            self._post_connect()

        if to_from_mismatch:
            raise HostMismatch()

    def stream_end(self):
        """Process </stream:stream> (stream end) tag received from peer.
        """
        logger.debug("Stream ended")
        self.eof = True
        if self._serializer:
            self._send_stream_end()
        if self._reader:
            self._reader = None
            self.features = None
        self.event(DisconnectedEvent(self.peer))

    def stanza(self, element):
        """Process stanza (first level child element of the stream).

        :Parameters:
            - `element`: stanza's full XML
        """
        self._process_element(element)

    def error(self, descr):
        """Handle stream XML parse error.

        :Parameters:
            - `descr`: error description
        """
        raise StreamParseError(descr)

    def _send_stream_end(self):
        """Send stream end tag."""
        data = self._serializer.emit_tail()
        try:
            self._write_raw(data.encode("utf-8"))
        except (IOError, SystemError, socket.error), err:
            logger.debug(u"Sending stream closing tag failed: {0}".format(err))
        self._serializer = None
        self.features = None

    def _send_stream_start(self, stream_id = None):
        """Send stream start tag."""
        if self._serializer:
            raise StreamError("Stream start already sent")
        if not self.language:
            self.language = self.settings["language"]
        self._serializer = XMPPSerializer(self.stanza_namespace,
                                        self.settings["extra_ns_prefixes"])
        if self.peer and self.initiator:
            stream_to = unicode(self.peer)
        else:
            stream_to = None
        if self.me and not self.initiator:
            stream_from = unicode(self.me)
        else:
            stream_from = None
        if stream_id:
            self.stream_id = stream_id
        else:
            self.stream_id = None
        head = self._serializer.emit_head(stream_from, stream_to,
                                    self.stream_id, language = self.language)
        self._write_raw(head.encode("utf-8"))

    def _send_stream_error(self, condition):
        """Send stream error element.

        :Parameters:
            - `condition`: stream error condition name, as defined in the
              XMPP specification."""
        if self.eof:
            return
        if not self._serializer:
            self._send_stream_start()
        element = StreamErrorElement(condition)
        data = self._serializer.emit_stanza(element)
        self._write_raw(data.encode("utf-8"))
        self._send_stream_end()

    def _restart_stream(self):
        """Restart the stream as needed after SASL and StartTLS negotiation."""
        self._reader = None
        self._serializer = None
        self.features = None
        if self.initiator:
            self._send_stream_start(self.stream_id)
        self._make_reader()

    def _make_stream_features(self):
        """Create the <features/> element for the stream.

        [receving entity only]

        :returns: new <features/> element
        :returntype: `ElementTree.Element`"""
        features = ElementTree.Element(STREAM_QNP + "features")
        return features

    def _send_stream_features(self):
        """Send stream <features/>.

        [receiving entity only]"""
        self.features = self._make_stream_features()
        data = self._serializer.emit_stanza(self.features)
        self._write_raw(data.encode("utf-8"))

    def write_raw(self, data):
        """Write raw data to the stream socket.

        :Parameters:
            - `data`: data to send
        :Types:
            - `data`: `bytes`"""
        with self.lock:
            return self._write_raw(data)

    def _write_raw(self, data):
        """Same as `Stream.write_raw` but assume `self.lock` is acquired."""
        logging.getLogger("pyxmpp.stream.out").debug("OUT: %r", data)
        try:
            while data:
                sent = self.socket.send(data)
                data = data[sent:]
        except (IOError, OSError, socket.error), err:
            raise FatalStreamError(u"IO Error: {0}".format(err))

    def _write_element(self, element):
        """Write XML `element` to the stream.

        :Parameters:
            - `element`: Element node to send.
        :Types:
            - `element`: `ElementTree.Element`
        """
        if self.eof or not self.socket or not self._serializer:
            logger.debug("Dropping stanza: {0}".format(
                                                    ElementTree.dump(element)))
            return
        data = self._serializer.emit_stanza(element)
        self._write_raw(data.encode("utf-8"))

    def send(self, stanza):
        """Write stanza to the stream.

        :Parameters:
            - `stanza`: XMPP stanza to send.
        :Types:
            - `stanza`: `pyxmpp2.stanza.Stanza`
        """
        with self.lock:
            return self._send(stanza)

    def _send(self, stanza):
        """Same as `Stream.send` but assume `self.lock` is acquired."""
        if self.version == (0, 9):
            legacy = True
        else:
            legacy = False
        self.fix_out_stanza(stanza)
        element = self.stanza.as_xml(legacy = legacy)
        self._write_element(element)

    def regular_tasks(self):
        """Do some housekeeping (cache expiration, timeout handling).

        This method should be called periodically from the application's
        main loop.
        
        :Return: suggested delay (in seconds) before the next call to this
                                                                    method.
        :Returntype: `int`
        """
        with self.lock:
            return self._regular_tasks()

    def _regular_tasks(self):
        """Same as `Stream.regular_tasks` but assume `self.lock` is acquired."""
        self._iq_response_handlers.expire()
        if not self.socket or self.eof:
            return 0
        now = time.time()
        if self.keepalive and now - self.last_keepalive >= self.keepalive:
            self._write_raw(" ")
            self.last_keepalive = now
            return min(self.keepalive, 
                                    self.settings[u"default_stanza_timeout"])
        else:
            return self.settings[u"default_stanza_timeout"]

    def fileno(self):
        """Return filedescriptor of the stream socket."""
        self.lock.acquire()
        try:
            if self.socket:
                return self.socket.fileno()
            else:
                return None
        finally:
            self.lock.release()

    def loop(self, timeout):
        """Simple "main loop" for the stream."""
        with self.lock:
            while not self.eof and self.socket is not None:
                act = self._loop_iter(timeout)
                if not act:
                    self._regular_tasks()

    def loop_iter(self, timeout):
        """Single iteration of a simple "main loop" for the stream."""
        with self.lock:
            return self._loop_iter(timeout)

    def _loop_iter(self, timeout):
        """Same as `Stream.loop_iter` but assume `self.lock` is acquired."""
        import select
        self.lock.release()
        try:
            if not self.socket:
                time.sleep(timeout)
                return False
            try:
                ifd, _unused, efd = select.select([self.socket], [],
                                                        [self.socket], timeout)
            except select.error, err:
                if err.args[0] != errno.EINTR:
                    raise
                ifd, _unused, efd = [], [], []
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
        with self.lock:
            self._process()

    def _process(self):
        """Same as `Stream.process` but assume `self.lock` is acquired."""
        try:
            try:
                self._read()
            except Exception, err:
                logger.exception("Exception during read()")
                raise
        except (IOError, OSError, socket.error), err:
            self.close()
            raise FatalStreamError("IO Error: "+str(err))
        except (FatalStreamError, KeyboardInterrupt, SystemExit), err:
            self.close()
            raise

    def _read(self):
        """Read data pending on the stream socket and pass it to the parser."""
        logger.debug("StreamBase._read(), socket: {0!r}", self.socket)
        if self.eof:
            return
        try:
            data = self.socket.recv(1024)
        except socket.error, err:
            if err.args[0] != errno.EINTR:
                raise
            return
        self._feed_reader(data)

    def _feed_reader(self, data):
        """Feed the stream reader with data received.

        If `data` is None or empty, then stream end (peer disconnected) is
        assumed and the stream is closed.

        :Parameters:
            - `data`: data received from the stream socket.
        :Types:
            - `data`: `unicode`
        """
        logging.getLogger("pyxmpp.stream.in").debug("IN: %r", data)
        if data:
            try:
                self._reader.feed(data)
            except StreamParseError:
                self._send_stream_error("xml-not-well-formed")
                raise
        else:
            self.eof = True
            self.disconnect()
            self.stream_end()

    def _process_element(self, element):
        """Process first level element of the stream.

        The element may be stream error or features, StartTLS
        request/response, SASL request/response or a stanza.

        :Parameters:
            - `element`: XML element
        :Types:
            - `element`: `ElementTree.Element`
        """
        tag = element.tag
        if tag.startswith(self._stanza_namespace_p):
            stanza = stanza_factory(element, self, self.language)
            self.lock.release()
            try:
                self.process_stanza(stanza)
            finally:
                self.lock.acquire()
        elif tag == ERROR_TAG:
            error = StreamErrorElement(element)
            self.lock.release()
            try:
                self.process_stream_error(error)
            finally:
                self.lock.acquire()
        elif tag == FEATURES_TAG:
            self.features = element
            self._got_features()
        else:
            logger.debug("Unhandled element: {0}".format(serialize(element)))

    def process_stream_error(self, error):
        """Process stream error element received.

        :Types:
            - `error`: `StreamErrorNode`

        :Parameters:
            - `error`: error received
        """

        logger.debug("Unhandled stream error: condition: {0} {1!r}"
                            .format(error.condition_name, error.serialize()))

    def check_to(self, to):
        """Check "to" attribute of received stream header.

        :return: `to` if it is equal to `self.me`, None otherwise.

        Should be overriden in derived classes which require other logic
        for handling that attribute."""
        if to != self.me:
            return None
        return to

    def generate_id(self):
        """Generate a random and unique stream ID.

        :return: the id string generated."""
        return uuid.uuid4()

    def _got_features(self):
        """Process incoming <stream:features/> element.

        [initiating entity only]

        The received features node is available in `self.features`."""
        has_bind_feature = False
        for element in self.features:
            if element.tag == FEATURE_BIND:
                has_bind_feature = True
        if self.authenticated:
            if has_bind_feature:
                self.bind(self.me.resource)
            else:
                self.event(AuthorizedEvent(self.me))

    def bind(self, resource):
        """Bind to a resource.

        [initiating entity only]

        :Parameters:
            - `resource`: the resource name to bind to.
        :Types:
            - `resource`: `unicode`

        XMPP stream is authenticated for bare JID only. To use
        the full JID it must be bound to a resource.
        """
        stanza = Iq(stanza_type = "set")
        element = ElementTree.Element(BIND_QNP + u"bind")
        stanza.set_payload(XMLPayload(element))
        self.event(BindingResourceEvent(resource))
        self.set_response_handlers(stanza, self._bind_success, self._bind_error)
        self.send(stanza)

    def _bind_success(self, stanza):
        """Handle resource binding success.

        [initiating entity only]

        :Parameters:
            - `stanza`: <iq type="result"/> stanza received.

        Set `self.me` to the full JID negotiated."""
        element = stanza.get_payload()
        jid = None
        for child in element:
            if child.tag == BIND_QNP + u"jid":
                jid = child.text
                break
        if not jid:
            raise BadRequestProtocolError(u"<jid/> element mising in"
                                                    " the bind response")
        self.me = JID(jid)
        self.event(AuthorizedEvent(self.me))

    def _bind_error(self, stanza): # pylint: disable-msg=R0201,W0613
        """Handle resource binding success.

        [initiating entity only]

        :raise FatalStreamError:"""
        raise FatalStreamError("Resource binding failed")

    def connected(self):
        """Check if stream is connected.

        :return: True if stream connection is active."""
        if self.connected and not self.eof:
            return True
        else:
            return False

# vi: sts=4 et sw=4
