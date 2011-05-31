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
# pylint: disable-msg=W0201

"""Core XMPP stream functionality.

Normative reference:
  - `RFC 6120 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import inspect
import socket
import time
import errno
import logging
import uuid
import re
from abc import ABCMeta
from functools import wraps

from xml.etree import ElementTree


from .xmppparser import XMLStreamHandler
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

from .streamevents import AuthorizedEvent, BindingResourceEvent
from .streamevents import ConnectedEvent, GotFeaturesEvent
from .streamevents import ConnectingEvent, ConnectionAcceptedEvent
from .streamevents import DisconnectedEvent, ResolvingAddressEvent
from .streamevents import ResolvingSRVEvent, StreamConnectedEvent
from .streamevents import AuthenticatedEvent

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

# just to distinguish those from a domain name
IP_RE = re.compile(r"^((\d+.){3}\d+)|([0-9a-f]*:[0-9a-f:]*:[0-9a-f]*)$")

class XMPPEventHandler:
    __metaclass__ = ABCMeta
    def handle_xmpp_event(self, event):
        return False

class StreamFeatureHandler:
    __metaclass__ = ABCMeta
    def handle_stream_features(self, stream, features):
        """Handle features announced by the stream peer.

        [initiator only]

        :Parameters:
            - `stream`: the stream
            - `features`: the features element just received
        :Types:
            - `stream`: `StreamBase`
            - `features`: `ElementTree.Element`
        """
        return False
    def make_stream_features(self, stream, features):
        """Update the features element announced by the stream.

        [receiver only]

        :Parameters:
            - `stream`: the stream
            - `features`: the features element about to be sent
        :Types:
            - `stream`: `StreamBase`
            - `features`: `ElementTree.Element`
        """
        return False

def stream_element_handler(element_name, usage_restriction = None):
    """Method decorator generator for decorating stream element
    handler methods in `StreamFeatureHandler` subclasses.
    
    :Parameters:
        - `element_name`: stream element QName
        - `usage_restriction`: optional usage restriction: "initiator" or
          "receiver"
    :Types:
        - `element_name`: `unicode`
        - `usage_restriction`: `unicode`
    """
    def decorator(func):
        """The decorator"""
        func._pyxmpp_stream_element_handled = element_name
        func._pyxmpp_usage_restriction = usage_restriction
        return func
    return decorator

def once(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            if func.__name__ in self._in_progress:
                raise AlreadyInProgress(func.__name__)
            self._in_progress.add(func.__name__)
        try:
            func(self, *args, **kwargs)
        finally:
            with self.lock:
                self._in_progress.remove(func.__name__)
    return wrapper

class StreamBase(StanzaProcessor, XMLStreamHandler):
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
        - `features`: stream features as annouced by the receiver.
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
    def __init__(self, stanza_namespace, handlers, settings = None):
        """Initialize StreamBase object

        :Parameters:
          - `stanza_namespace`: stream's default namespace URI ("jabber:client"
            for client, "jabber:server" for server, etc.)
          - `handlers`: objects to handle the stream events and elements
          - `settings`: extra settings
        :Types:
          - `stanza_namespace`: `unicode`
          - `settings`: XMPPSettings
          - `handlers`: `list` of objects
        """
        XMLStreamHandler.__init__(self)
        if settings is None:
            settings = XMPPSettings()
        self.settings = settings
        StanzaProcessor.__init__(self, settings[u"default_stanza_timeout"])
        self.stanza_namespace = stanza_namespace
        self._stanza_namespace_p = "{{{0}}}".format(stanza_namespace)
        self.keepalive = self.settings[u"keepalive"]
        self.process_all_stanzas = False
        self.port = None
        self.handlers = handlers
        self._event_handlers = []
        self._stream_feature_handlers = []
        for handler in handlers:
            if isinstance(handler, XMPPEventHandler):
                self._event_handlers.append(handler)
            if isinstance(handler, StreamFeatureHandler):
                self._stream_feature_handlers.append(handler)
        self._in_progress = set()
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
        self.finished = False

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
        self._setup_stream_element_handlers()
        self.setup_stanza_handlers(self.handlers, "pre-auth")
        self._send_stream_start()
        self._make_reader()

    @once
    def connect(self, addr, port = None, service = None, to = None):
        """Establish XMPP connection with given address.

        One of: `port` or `service` must be provided and `addr` must be 
        a domain name and not an IP address `port` is not given.

        When `service` is given try an SRV lookup for that service
        at domain `addr`. If `service is not given or `addr` is an IP address, 
        or the SRV lookup fails, connect to `port` at host `addr` directly.

        [initiating entity only]

        :Parameters:
            - `addr`: peer name or IP address
            - `port`: port number to connect to
            - `service`: service name (to be resolved using SRV DNS records)
            - `to`: peer name if different than `addr`
        """
        if to is None:
            to = unicode(addr)
        srv_used = False
        self.selected_host = None
        if service is not None and not IP_RE.match(addr):
            self.event(ResolvingSRVEvent(addr, service))
            addrs = resolver.resolve_srv(addr, service)
            if addrs:
                srv_used = True
            elif port:
                addrs = [(addr, port)]
            else:
                raise DNSError("Could not resolve SRV for service {0!r}"
                            " on host {1!r} and fallback port number not given"
                                                        .format(service, addr))
        elif port:
            addrs = [(addr, port)]
        else:
            raise ValueError("No port number or service name given")
        exception = None
        for addr, port in addrs:
            if type(addr) in (str, unicode):
                self.event(ResolvingAddressEvent(addr))
            sock = None
            while True:
                try:
                    addresses = resolver.getaddrinfo(addr, port, None,
                                socket.SOCK_STREAM, allow_cname = not srv_used)
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
                    if srv_used:
                        self.selected_host = addr
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
        with self.lock:
            self.addr = addr
            self.port = port
            self._connect_socket(sock, to)
            self.last_keepalive = time.time()
        self.event(ConnectedEvent(sockaddr))

    def accept(self, sock, myname):
        """Accept incoming connection.

        [receiving entity only]

        :Parameters:
            - `sock`: a listening socket.
            - `myname`: local stream endpoint name.
        """
        with self.lock:
            addr = self._accept(sock, myname)
        self.event(ConnectionAcceptedEvent(addr))

    def _accept(self, sock, myname):
        """Same as `Stream.accept` but assume `self.lock` is acquired
        and does not emit the `ConnectionAcceptedEvent`."""
        self.eof = False
        self.socket, addr = sock.accept()
        logger.debug("Connection from: %r" % (addr,))
        self.addr, self.port = addr
        if myname:
            self.me = JID(myname)
        else:
            self.me = None
        self.initiator = False
        self._make_reader()
        self.last_keepalive = time.time()
        self._setup_stream_element_handlers()
        self.setup_stanza_handlers(self.handlers, "pre-auth")
        return addr

    def _setup_stream_element_handlers(self):
        """Set up stream element handlers.
        
        Scans the `self.handlers` list for `StreamFeatureHandler`
        instances and updates `self._element_handlers` mapping with their
        methods decorated with `@stream_element_handler`"""
        if self.initiator:
            mode = "initiator"
        else:
            mode = "receiver"
        self._element_handlers = {}
        for handler in self.handlers:
            if not isinstance(handler, StreamFeatureHandler):
                continue
            for name, meth in inspect.getmembers(handler, callable):
                if not hasattr(meth, "_pyxmpp_stream_element_handled"):
                    continue
                element_handled = meth._pyxmpp_stream_element_handled
                if element_handled in self._element_handlers:
                    # use only the first matching handler
                    continue
                if meth._pyxmpp_usage_restriction in (None, mode):
                    self._element_handlers[element_handled] = meth

    def disconnect(self):
        """Gracefully close the connection."""
        with self.lock:
            return self._disconnect()

    def _disconnect(self):
        """Same as `Stream.disconnect` but assume `self.lock` is acquired."""
        if self._serializer:
            # output stream open - close it
            self._send_stream_end()
        if self._reader is None:
            # input stream not started or already finished
            self._close()

    def event(self, event): # pylint: disable-msg=R0201
        """Handle a stream event.
        
        Called when connection state is changed.

        Should not be called with self.lock acquired!
        """
        event.stream = self
        logger.debug(u"Stream event: {0}".format(event))
        for handler in self._event_handlers:
            logger.debug(u"  passing the event to: {0!r}".format(handler))
            if handler.handle_xmpp_event(event):
                return True
        return False

    def close(self):
        """Forcibly close the connection and clear the stream state."""
        with self.lock:
            return self._close()

    def _close(self):
        """Same as `Stream.close` but assume `self.lock` is acquired."""
        if self._reader:
            self._reader = None
        if self._serializer:
            self._send_stream_end()
        if self.socket is not None:
            self.socket.close()
            self.socket = None
            self.event(DisconnectedEvent(self.peer))
        self.finished = True

    def _make_reader(self):
        """Create ne `StreamReader` instace as `self._reader`."""
        self._reader = StreamReader(self)

    def stream_start(self, element):
        """Process <stream:stream> (stream start) tag received from peer.
        
        `self.lock` is acquired when this method is called.

        :Parameters:
            - `element`: root element (empty) created by the parser"""
        logger.debug("input document: " + ElementTree.tostring(element))
        if not element.tag.startswith(STREAM_QNP):
            self._send_stream_error("invalid-namespace")
            raise FatalStreamError("Bad stream namespace")

        version = element.get("version")
        if version:
            try:
                major, minor = version.split(".", 1)
                major, minor = int(major), int(minor)
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

        self.lock.release()
        try:
            self.event(StreamConnectedEvent(self.peer))
        finally:
            self.lock.acquire()

        if to_from_mismatch:
            raise HostMismatch()

    def stream_end(self):
        """Process </stream:stream> (stream end) tag received from peer.
        
        `self.lock` is acquired when this method is called.
        """
        logger.debug("Stream ended")
        self.eof = True
        if self._reader:
            self._reader = None
            self.features = None
        if self._serializer:
            self._send_stream_end()
        self._close()

    def stream_element(self, element):
        """Process first level child element of the stream).

        `self.lock` is acquired when this method is called.

        :Parameters:
            - `element`: stanza's full XML
        """
        self._process_element(element)

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
        element = StreamErrorElement(condition).as_xml()
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
        self.unset_iq_set_handler(XMLPayload, FEATURE_BIND)

    def _make_stream_features(self):
        """Create the <features/> element for the stream.

        [receving entity only]

        :returns: new <features/> element
        :returntype: `ElementTree.Element`"""
        features = ElementTree.Element(FEATURES_TAG)
        for handler in self._stream_feature_handlers:
            handler.make_stream_features(self, features)
        return features

    def _send_stream_features(self):
        """Send stream <features/>.

        [receiving entity only]"""
        self.features = self._make_stream_features()
        self._write_element(self.features)

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

    def write_element(self, element):
        """Write XML `element` to the stream.

        :Parameters:
            - `element`: Element node to send.
        :Types:
            - `element`: `ElementTree.Element`
        """
        with self.lock:
            self._write_element(element)

    def _write_element(self, element):
        """Same as `write_element` but with `self.lock` already acquired.
        """
        if self.eof or not self.socket or not self._serializer:
            logger.debug("Dropping element: {0}".format(
                                                ElementTree.tostring(element)))
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
        self.fix_out_stanza(stanza)
        element = stanza.as_xml()
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
                logger.debug("Exception during read()", exc_info = True)
                raise
        except (IOError, OSError, socket.error), err:
            self.close()
            raise FatalStreamError("IO Error: "+str(err))
        except (FatalStreamError, KeyboardInterrupt, SystemExit), err:
            self.close()
            raise

    def _read(self):
        """Read data pending on the stream socket and pass it to the parser."""
        logger.debug("StreamBase._read(), socket: {0!r}".format(self.socket))
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

        `self.lock` is acquired during the operation.

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
        if tag in self._element_handlers:
            self.lock.release()
            try:
                handler = self._element_handlers[tag]
                logger.debug("Passing element {0!r} to method {1!r}"
                                                    .format(element, handler))
                handled = handler(self, element)
            finally:
                self.lock.acquire()
            if handled:
                return
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
            logger.debug("Got features element: {0}".format(serialize(element)))
            self.features = element
            self._got_features()
        else:
            logger.debug("Unhandled element: {0}".format(serialize(element)))
            logger.debug(" known handlers: {0!r}".format(
                                                    self._element_handlers))

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
        return unicode(uuid.uuid4())

    def _got_features(self):
        """Process incoming <stream:features/> element.

        [initiating entity only]

        The received features node is available in `self.features`."""
        self.lock.release()
        try:
            logger.debug("got features, passing to event handlers...")
            handled = self.event(GotFeaturesEvent(self.features))
            logger.debug("  handled: {0}".format(handled))
            if not handled:
                logger.debug("  passing to stream features handlers: {0}"
                                        .format(self._stream_feature_handlers))
                for handler in self._stream_feature_handlers:
                    handled = handler.handle_stream_features(self,
                                                                self.features)
                    if handled:
                        break
        finally:
            self.lock.acquire()

    def connected(self):
        """Check if stream is connected.

        :return: True if stream connection is active."""
        if self.socket and not self.eof:
            return True
        else:
            return False

    def set_peer_authenticated(self, peer, restart_stream = False):
        with self.lock:
            self.peer_authenticated = True
            self.peer = peer
            if restart_stream:
                self._restart_stream()
        self.setup_stanza_handlers(self.handlers, "post-auth")
        self.event(AuthenticatedEvent(self.peer))

    def set_authenticated(self, me, restart_stream = False):
        with self.lock:
            self.authenticated = True
            self.me = me
            if restart_stream:
                self._restart_stream()
        self.setup_stanza_handlers(self.handlers, "post-auth")
        self.event(AuthenticatedEvent(self.me))

# vi: sts=4 et sw=4
