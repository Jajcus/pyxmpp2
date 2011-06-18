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

"""XMPP transport.

This module provides the abstract base class for XMPP transports (mechanisms
used to send and receive XMPP content, not to be confused with protocol
gateways sometimes also called 'transports') and the standard TCP transport.
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import socket
import threading
import errno
import logging

from functools import partial
from abc import ABCMeta
from xml.etree import ElementTree

from .mainloop.abc import IOHandler, HandlerReady, PrepareAgain
from .settings import XMPPSettings
from .exceptions import DNSError, PyXMPPIOError
from .streamevents import ResolvingSRVEvent, ResolvingAddressEvent
from .streamevents import ConnectedEvent, ConnectingEvent, DisconnectedEvent
from .xmppserializer import XMPPSerializer
from .xmppparser import StreamReader
from . import resolver

logger = logging.getLogger("pyxmpp.transport")

class XMPPTransport:
    """Abstract base class for XMPP transport implementations."""
    # pylint: disable-msg=R0922,W0232
    __metaclass__ = ABCMeta
    def set_target(self, stream):
        """Make the `stream` the target for this transport instance.

        The `stream_start`, `stream_end` and `stream_element` methods
        of the target will be called when appropriate content is received.

        :Parameters:
            - `stream`: the stream handler to receive stream content
              from the transport
        :Types:
            - `stream`: `StreamBase`
        """
        raise NotImplementedError

    def send_stream_head(self, stanza_namespace, stream_from, stream_to,
                        stream_id = None, version = u'1.0', language = None):
        """
        Send stream head via the transport.

        :Parameters:
            - `stanza_namespace`: namespace of stream stanzas (e.g.
              'jabber:client')
            - `stream_from`: the 'from' attribute of the stream. May be `None`.
            - `stream_to`: the 'to' attribute of the stream. May be `None`.
            - `version`: the 'version' of the stream.
            - `language`: the 'xml:lang' of the stream
        :Types:
            - `stazna_namespace`: `unicode`
            - `stream_from`: `unicode`
            - `stream_to`: `unicode`
            - `version`: `unicode`
            - `language`: `unicode`
        """
        # pylint: disable-msg=R0913
        raise NotImplementedError

    def send_stream_tail(self):
        """
        Send stream tail via the transport.
        """
        raise NotImplementedError

    def send_element(self, element):
        """
        Send an element via the transport.
        """
        raise NotImplementedError

    def is_connected(self):
        """
        Check if the transport is connected.

        :Return: `True` if is connected.
        """
        raise NotImplementedReturn

    def disconnect(self):
        """
        Gracefully disconnect the connection.
        """
        raise NotImplementedError

class TCPTransport(XMPPTransport, IOHandler):
    """XMPP over TCP with optional TLS"""
    # pylint: disable-msg=R0902
    def __init__(self, settings = None, sock = None):
        """Initialize the `TCPTransport object.

        :Parameters:
            - `settings`: XMPP settings to use
            - `sock`: existing socket, e.g. for accepted incoming connection.
        """
        if settings:
            self.settings = settings
        else:
            self.settings = XMPPSettings()
        self.lock = threading.RLock()
        self._writability_cond = threading.Condition(self.lock)
        self._eof = False
        self._hup = False
        self._stream = None
        self._serializer = None
        self._reader = None
        self._first_head_written = False
        self._dst_name = None
        self._dst_port = None
        self._dst_service = None
        self._dst_nameports = None
        self._dst_hostname = None
        self._dst_addrs = None
        if sock is None:
            self._socket = None
            self._blocking = True
            self._dst_addr = None
            self._family = None
            self._state = None
        else:
            self._socket = sock
            self._family = sock.family
            self._dst_addr = sock.getpeername()
            self._state = "connected"
            self._blocking = sock.gettimeout() is not None
        self._event_queue = None

    def connect(self, addr, port = None, service = None):
        """Start establishing TCP connection with given address.

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
        """
        with self.lock:
            self._connect(addr, port, service)

    def _connect(self, addr, port, service):
        """Same as `connect`, but assumes `self.lock` acquired.
        """
        self._dst_name = addr
        self._dst_port = port
        family = None
        try:
            res = socket.getaddrinfo(addr, port, socket.AF_UNSPEC,
                                socket.SOCK_STREAM, 0, socket.AI_NUMERICHOST)
            family = res[0][0]
            sockaddr = res[0][4]
        except socket.gaierror:
            family = None
            sockaddr = None

        if family is not None:
            if not port:
                raise ValueError("No port number given with literal IP address")
            self._dst_service = None
            self._family = family
            self._dst_addrs = [(family, sockaddr)]
            self._state = "connect"
        elif service is not None:
            self._dst_service = service
            self._state = "resolve-srv"
            self._dst_name = addr
        elif port:
            self._dst_nameports = [(self._dst_name, self._dst_port)]
            self._dst_service = None
            self._state = "resolve-hostname"
        else:
            raise ValueError("No port number and no SRV service name given")

    def _resolve_srv(self):
        """Start resolving the SRV record.
        """
        resolver = self.settings["dns_resolver"]
        self._state = "resolving-srv"
        resolver.resolve_srv(self._dst_name, self._dst_service, "tcp",
                                                    callback = self._got_srv)
        self.event(ResolvingSRVEvent(self._dst_name))

    def _got_srv(self, addrs):
        """Handle SRV lookup result.
        
        :Parameters:
            - `addrs`: properly sorted list of (hostname, port) tuples
        """
        with self.lock:
            if not addrs:
                self._dst_service = None
                if self._dst_port:
                    self._dst_nameports = (self._dst_name, self._dst_port)
                else:
                    self._dst_nameports = []
                    self._state = "aborted"
                    raise DNSError("Could not resolve SRV for service {0!r}"
                            " on host {1!r} and fallback port number not given"
                                    .format(self._dst_service, self._dst_name))
            elif addrs == [(".", 0)]:
                self._dst_nameports = []
                self._state = "aborted"
                raise DNSError("Service {0!r} not available on host {1!r}"
                                    .format(self._dst_service, self._dst_name))
            else:
                self._dst_nameports = addrs
            self._state = "resolve-hostname"

    def _resolve_hostname(self):
        """Start hostname resolution for the next name to try.

        [called with `self.lock` acquired]
        """
        self._state = "resolving-hostname"
        resolver = self.settings["dns_resolver"]
        name, port = self._dst_nameports.pop(0)
        resolver.resolve_address(name, callback = partial(
                                self._got_addresses, name, port),
                                allow_cname = self._dst_service is None)
        self.event(ResolvingAddressEvent(name))

    def _got_addresses(self, name, port, addrs):
        """Handler DNS address record lookup result.
        
        :Parameters:
            - `name`: the name requested
            - `port`: port number to connect to
            - `addrs`: list of (family, address) tuples
        """
        with self.lock:
            if not addrs:
                if self._dst_nameports:
                    self._state = "resolve-hostname"
                    return
                else:
                    self._dst_addrs = []
                    self._state = "aborted"
                    raise DNSError("Could not resolve address record for {0!r}"
                                                                .format(name))
            else:
                self._dst_nameports = addrs
            self._dst_addrs = [ (family, (addr, port)) for (family, addr)
                                                                    in addrs ]
            self._state = "connect"

    def _start_connect(self):
        """Start connecting to the next address on the `self._dst_addrs`
        list.

        [ called with `self.lock` acquired ] 
        
        """
        family, addr = self._dst_addrs.pop(0)
        if not self._socket or self._family != family:
            self._socket = socket.socket(family, socket.SOCK_STREAM)
        self._dst_addr = addr
        self._family  = family
        self._socket.setblocking(False)
        try:
            self._socket.connect(addr)
        except socket.error, err:
            if err.args[0] == errno.EINPROGRESS:
                self._state = "connecting"
                self._writability_cond.notify()
                self.event(ConnectingEvent(addr))
            elif self._dst_addrs:
                self._state = "connect"
                return None
            elif self._dst_nameports:
                self._state = "resolve-hostname"
                return None
            else:
                self._socket.close()
                self._socket = None
                self._state = "aborted"
                self._writability_cond.notify()
                raise
        if self._blocking:
            logger.debug("_start_connect: making the socket blocking again.")
            self._socket.setblocking(True)
        self._state = "connected"
        self._stream.transport_connected()
        self.event(ConnectedEvent(self._dst_addr))

    def _continue_connect(self):
        """Continue connecting.

        [called with `self.lock` acquired]

        :Return: `True` when just connected
        """
        if self._blocking:
            logger.debug("_continue_connect: making the socket blocking again.")
            self._socket.setblocking(True)
        try:
            self._socket.connect(self._dst_addr)
        except socket.error, err:
            if err.args[0] == errno.EINPROGRESS:
                return None
            elif self._dst_addrs:
                self._state = "connect"
                return None
            elif self._dst_nameports:
                self._state = "resolve-hostname"
                return None
            else:
                self._socket.close()
                self._socket = None
                self._state = "aborted"
                raise
        self._state = "connected"
        self._stream.transport_connected()
        self.event(ConnectedEvent(self._dst_addr))

    def _write(self, data):
        """Write raw data to the socket.

        :Parameters:
            - `data`: data to send
        :Types:
            - `data`: `bytes`
        """
        logging.getLogger("pyxmpp.tcp.out").debug("OUT: %r", data)
        if self._hup or not self._socket:
            raise PyXMPPIOError(u"Connection closed.")
        try:
            while data:
                sent = self._socket.send(data)
                data = data[sent:]
        except (IOError, OSError, socket.error), err:
            raise PyXMPPIOError(u"IO Error: {0}".format(err))

    def set_target(self, stream):
        """Make the `stream_handler` the target for this transport instance.

        The `stream_start`, `stream_end` and `stream_element` methods
        of the target will be called when appropriate content is received.

        :Parameters:
            - `stream`: the stream handler to receive stream content
              from the transport
        :Types:
            - `stream`: `StreamBase`
        """
        with self.lock:
            if self._stream:
                raise ValueError("Target stream already set")
            self._stream = stream
            self._reader = StreamReader(stream)
            self._stream.event_queue = self._event_queue

    def send_stream_head(self, stanza_namespace, stream_from, stream_to, 
                        stream_id = None, version = u'1.0', language = None):
        """
        Send stream head via the transport.

        :Parameters:
            - `stanza_namespace`: namespace of stream stanzas (e.g.
              'jabber:client')
            - `stream_from`: the 'from' attribute of the stream. May be `None`.
            - `stream_to`: the 'to' attribute of the stream. May be `None`.
            - `version`: the 'version' of the stream.
            - `language`: the 'xml:lang' of the stream
        :Types:
            - `stanza_namespace`: `unicode`
            - `stream_from`: `unicode`
            - `stream_to`: `unicode`
            - `version`: `unicode`
            - `language`: `unicode`
        """
        # pylint: disable-msg=R0913
        with self.lock:
            self._serializer = XMPPSerializer(stanza_namespace,
                                            self.settings["extra_ns_prefixes"])
            head = self._serializer.emit_head(stream_from, stream_to,
                                                stream_id, version, language)
            self._write(head.encode("utf-8"))

    def send_stream_tail(self):
        """
        Send stream tail via the transport.
        """
        with self.lock:
            if not self._socket or self._hup:
                logger.debug(u"Cannot send stream closing tag: already closed")
                return
            data = self._serializer.emit_tail()
            try:
                self._write(data.encode("utf-8"))
            except (IOError, SystemError, socket.error), err:
                logger.debug(u"Sending stream closing tag failed: {0}"
                                                                .format(err))
            self._serializer = None
            self._hup = True
            try:
                self._socket.shutdown(socket.SHUT_WR)
            except socket.error:
                pass
            self._state = "closing"
            self._writability_cond.notify()

    def send_element(self, element):
        """
        Send an element via the transport.
        """
        with self.lock:
            if self._eof or self._socket is None or not self._serializer:
                logger.debug("Dropping element: {0}".format(
                                                ElementTree.tostring(element)))
                return
            data = self._serializer.emit_stanza(element)
            self._write(data.encode("utf-8"))

    def prepare(self):
        """When connecting start the next connection step and schedule
        next `prepare` call, when connected return `HandlerReady()`
        """
        result = HandlerReady()
        logger.debug("TCPHandler.prepare(): state: {0!r}".format(self._state))
        with self.lock:
            if self._state in ("connected", "established", "closing", "closed",
                                                                    "aborted"):
                # no need to call prepare() .fileno() is stable
                pass
            elif self._state == "connect":
                self._start_connect()
                result = PrepareAgain(None)
            elif self._state == "resolve-hostname":
                self._resolve_hostname()
                result = PrepareAgain(0)
            elif self._state == "resolve-srv":
                self._resolve_srv()
                result = PrepareAgain(0)
            else:
                # wait for i/o, but keep calling prepare()
                result = PrepareAgain(None)
        logger.debug("TCPHandler.prepare(): new state: {0!r}"
                                                        .format(self._state))
        return result

    def fileno(self):
        """Return file descriptor to poll or select."""
        with self.lock:
            if self._socket is not None:
                return self._socket.fileno()
        return None
    
    def set_event_queue(self, queue):
        with self.lock:
            self._event_queue = queue
            if self._stream:
                self._stream.event_queue = self._event_queue

    def set_blocking(self, blocking = True):
        """Force the handler into blocking mode, so the `handle_write()`
        and `handle_read()` methods are guaranteed to block (or fail if not
        `is_readable()` or `is_writable()` if nothing can be written or there is
        nothing to read.
        """
        with self.lock:
            if self._socket is None or blocking == self._blocking:
                return
            self._blocking = blocking
            self._socket.setblocking(blocking)

    def is_readable(self):
        """
        :Return: `True` when the I/O channel can be read
        """
        return self._socket is not None and not self._eof and (
                                    self._state in ("connected", "closing"))

    def wait_for_readability(self):
        """
        Stop current thread until the channel is readable.

        :Return: `False` if it won't be readable (e.g. is closed)
        """
        return self._socket is not None and not self._eof

    def is_writable(self):
        """
        :Return: `False` as currently the data is always written synchronously
        """
        with self.lock:
            return self._socket and self._state == "connecting"

    def wait_for_writability(self):
        """
        Stop current thread until the channel is writable.

        :Return: `False` if it won't be readable (e.g. is closed)
        """
        with self.lock:
            while True:
                if self._state in ("closing", "closed", "aborted"):
                    return False
                self._writability_cond.wait()
                if self.is_writable():
                    return True
        return False

    def handle_write(self):
        """
        Handle the 'channel writable' state. E.g. send buffered data via a
        socket.
        """
        events = []
        with self.lock:
            if self._state == "connecting":
                self._continue_connect()

    def handle_read(self):
        """
        Handle the 'channel readable' state. E.g. read from a socket.
        """
        with self.lock:
            if self._eof or self._socket is None:
                return
            while True:
                try:
                    data = self._socket.recv(4096)
                except socket.error, err:
                    if err.args[0] == errno.EINTR:
                        continue
                    elif err.args[0] == errno.EWOULDBLOCK:
                        break
                self._feed_reader(data)
                if self._blocking or not data:
                    break

    def handle_hup(self):
        """
        Handle the 'channel hungup' state. The handler should not be writtable
        after this.
        """
        self._hup = True

    def handle_err(self):
        """
        Handle an error reported.
        """
        with self.lock:
            self._socket.close()
            self._socket = None
            self._state = "aborted"
            self._writability_cond.notify()
        raise PyXMPPIOError("Unhandled error on socket")

    def handle_nval(self):
        """
        Handle an error reported.
        """
        if self._socket is None:
            # socket closed by other thread
            return
        self._state = "aborted"
        raise PyXMPPIOError("Invalid file descriptor used in main event loop")

    def is_connected(self):
        """
        Check if the transport is connected.

        :Return: `True` if is connected.
        """
        return self._state == "connected" and not self._eof and not self._hup

    def disconnect(self):
        """Disconnect the stream gracefully."""
        logger.debug("TCPTransport.disconnect()")
        with self.lock:
            if self._socket is None:
                if self._state != "closed":
                    self.event(DisconnectedEvent(self._dst_addr))
                    self._state = "closed"
                return
            if self._hup or not self._serializer:
                self._close()
            else:
                self.send_stream_tail()

    def close(self):
        """Close the stream immediately, so it won't expect more events."""
        with self.lock:
            self._close()

    def _close(self):
        if self._state != "closed":
            self.event(DisconnectedEvent(self._dst_addr))
            self._state = "closed"
        if self._socket is None:
            return
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self._socket.close()
        self._socket = None
        self._writability_cond.notify()

    def _feed_reader(self, data):
        """Feed the stream reader with data received.

        [ called with `self.lock` acquired ] 

        If `data` is None or empty, then stream end (peer disconnected) is
        assumed and the stream is closed.

        `self.lock` is acquired during the operation.

        :Parameters:
            - `data`: data received from the stream socket.
        :Types:
            - `data`: `unicode`
        """
        logging.getLogger("pyxmpp.tcp.in").debug("IN: %r", data)
        if data:
            self._reader.feed(data)
        else:
            self._eof = True
            self._stream.stream_eof()
            if not self._serializer:
                if self._state != "closed":
                    self.event(DisconnectedEvent(self._dst_addr))
                    self._state = "closed"

    def event(self, event):
        """Pass an event to the target stream or just log it."""
        logger.debug(u"TCP transport event: {0}".format(event))
        if self._stream:
            event.stream = self._stream
        if self._event_queue:
            self._event_queue.post_event(event)

