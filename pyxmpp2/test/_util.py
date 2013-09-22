#!/usr/bin/python

"""Utilities for pyxmmp2 unit tests."""

import time
import unittest
import socket
import threading
import select
import logging
import ssl
import errno

from pyxmpp2.test import _support

from pyxmpp2.streamevents import DisconnectedEvent

from pyxmpp2.transport import TCPTransport
from pyxmpp2.mainloop.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.mainloop.select import SelectMainLoop
from pyxmpp2.mainloop.poll import PollMainLoop
from pyxmpp2.mainloop.threads import ThreadPool
from pyxmpp2.settings import XMPPSettings

logger = logging.getLogger("pyxmpp2.test._util")

socket.setdefaulttimeout(5)

TIMEOUT = 60.0 # seconds

class NetReaderWritter(object):
    """Threaded network reader/writter.

    :Ivariables:
        - `sock`: the socket
        - `wdata`: data to be sent
        - `rdata`: data received
        - `eof`: EOF flag
        - `error`: error flag
        - `peer`: address of the peer connected
    """
    # pylint: disable=R0902
    def __init__(self, sock, need_accept = False):
        self.sock = sock
        self.wdata = b""
        self.rdata = b""
        self.eof = False
        self.ready = not need_accept
        self._disconnect = False
        self.write_enabled = True
        self.lock = threading.RLock()
        self.write_cond = threading.Condition(self.lock)
        self.eof_cond = threading.Condition(self.lock)
        self.extra_on_read = None
        self.peer = None

    def start(self):
        """Start the reader and writter threads."""
        reader_thread = threading.Thread(target = self.reader_run,
                                                            name = "Reader")
        reader_thread.daemon = True
        writter_thread = threading.Thread(target = self.writter_run,
                                                            name = "Writter")
        writter_thread.daemon = True
        reader_thread.start()
        writter_thread.start()

    def _do_tls_handshake(self):
        """Do the TLS handshake. Called from the reader thread
        after `starttls` is called."""
        logger.debug("tst: starting tls handshake")
        while True:
            try:
                self.sock.do_handshake()
                break
            except ssl.SSLError, err:
                if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                    select.select([self.sock], [], [])
                elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                    select.select([], [self.sock], [])
                else:
                    raise
        logger.debug("tst: tls handshake started, resuming normal write")
        self.extra_on_read = None
        self.write_enabled = True
        self.write_cond.notify()

    def starttls(self, *args, **kwargs):
        """Request switching to TLS.

        First waits untill all currently buffered data is sent.

        :Parameters:
            - `args`: positional arguments to :std:`ssl.wrap_socket`
            - `kwargs`: keyword arguments to :std:`ssl.wrap_socket`
        """
        kwargs['do_handshake_on_connect'] = False
        with self.lock:
            # flush write buffer
            logger.debug("tst: flushing write buffer before tls wrap")
            while self.wdata:
                self.write_cond.wait()
            self.write_enabled = False
            self.write_cond.notify()
            logger.debug("tst: wrapping the socket")
            self.sock = ssl.wrap_socket(*args, **kwargs)
            self.extra_on_read = self._do_tls_handshake
            self.rdata = b""

    def writter_run(self):
        """The writter thread function."""
        with self.write_cond:
            while self.sock is not None:
                while self.ready and self.wdata and self.write_enabled:
                    sent = self.sock.send(self.wdata)
                    logger.debug(u"tst OUT: " + repr(self.wdata[:sent]))
                    self.wdata = self.wdata[sent:]
                    self.write_cond.notify()
                if self._disconnect and not self.wdata:
                    self.sock.shutdown(socket.SHUT_WR)
                    logger.debug(u"tst OUT: EOF")
                    break
                self.write_cond.wait()

    def reader_run(self):
        """The reader thread function."""
        WSAEBADF = getattr(errno, "WSAEBADF", None)
        with self.lock:
            if not self.sock or self.eof:
                return
            while not self.eof and self.sock is not None:
                self.lock.release()
                try:
                    ret = infd, _outfd, _errfd = select.select([self.sock], [],
                                                                        [], 5)
                except select.error, err:
                    if WSAEBADF and err == WSAEBADF:
                        self.sock = None
                        break
                    raise
                finally:
                    self.lock.acquire()
                if not self.sock:
                    break
                if infd:
                    if self.extra_on_read:
                        self.extra_on_read()
                    elif self.ready:
                        data = self.sock.recv(1024)
                        if not data:
                            logger.debug(u"tst IN: EOF")
                            self.eof = True
                            self.eof_cond.notifyAll()
                        else:
                            logger.debug(u"tst IN: " + repr(data))
                            self.rdata += data
                    else:
                        sock1, self.peer = self.sock.accept()
                        logger.debug(u"tst ACCEPT: " + repr(self.peer))
                        self.sock.close()
                        self.sock = sock1
                        self.ready = True
                        self.write_cond.notify()

    def write(self, data):
        """Queue data for write."""
        with self.write_cond:
            self.wdata += data
            if self.ready:
                self.write_cond.notify()

    def disconnect(self):
        """Request disconnection."""
        with self.write_cond:
            self._disconnect = True
            self.write_cond.notify()

    def read(self):
        """Read data from input buffer (received by the reader thread)."""
        with self.lock:
            data, self.rdata = self.rdata, ""
        return data

    def close(self):
        """Close the socket and request the threads to stop."""
        with self.lock:
            if self.sock is not None:
                self.sock.close()
            self.sock = None
            self.wdata = None
            self.write_cond.notify()
            self.eof_cond.wait(0.1)

    def wait(self, timeout):
        """Wait for socket closing, an error or `timeout` seconds."""
        with self.eof_cond:
            if not self.eof:
                self.eof_cond.wait(timeout)

class NetworkTestCase(unittest.TestCase):
    """Base class for networking test cases.

    :Variables:
        - `can_do_ipv4`: `True` if IPv4 sockets are available
        - `can_do_ipv6`: `True` if IPv6 sockets are available

    :Ivariables:
        - `server`: a server for testing client connections (created by
          `start_server`)
        - `client`: a client for testing server connections (created by
          `start_client`)
    :Types:
        - `server`: `NetReaderWritter`
        - `client`: `NetReaderWritter`
    """
    can_do_ipv4 = False
    can_do_ipv6 = False
    @classmethod
    def setUpClass(cls):
        """Check if loopback networking is enabled and IPv4 and IPv6 sockets
        available."""
        if "lo-network" not in _support.RESOURCES:
            raise unittest.SkipTest("loopback network usage disabled")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.close()
            cls.can_do_ipv4 = True
        except socket.error, err:
            logger.debug("socket error: {0} while testing IPv4".format(err))
            pass
        if socket.has_ipv6:
            try:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.close()
                cls.can_do_ipv6 = True
            except socket.error, err:
                logger.debug("socket error: {0} while testing IPv6".format(err))
                pass

    def setUp(self):
        """Initialize class instance for a new test."""
        self.server = None
        self.client = None
        # pylint: disable=W0212
        # reset the event queue
        XMPPSettings._defs['event_queue'].default = None

    def tearDown(self):
        """Stop the server and client connections started."""
        if self.server:
            self.server.close()
        if self.client:
            self.client.close()
        # pylint: disable=W0212
        # reset the event queue
        XMPPSettings._defs['event_queue'].default = None

    def start_server(self, ip_version = 4):
        """Create the `server` object, start its thread and return
        assigned socket address (IP address, port)."""
        sock = self.make_listening_socket(ip_version)
        self.server = NetReaderWritter(sock, need_accept = True)
        self.server.start()
        return sock.getsockname()

    def make_listening_socket(self, ip_version = 4):
        """Create a listening socket on a random (OS-assigned) port
        on the loopback interface."""
        if ip_version == 4:
            if not self.can_do_ipv4:
                self.skipTest("Networking not available")
                return None
            family = socket.AF_INET
            addr = "127.0.0.1"
        elif ip_version == 6:
            if not self.can_do_ipv6:
                self.skipTest("IPv6 networking not available")
                return None
            family = socket.AF_INET6
            addr = "::1"
        else:
            raise ValueError, "Bad IP version"
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.bind((addr, 0))
        sock.listen(1)
        return sock

    def start_client(self, sockaddr, ip_version = 4):
        """Create the `client` object, starts its threads anc
        connect it to the provided `sockaddr`.

        :Return: its socket address"""
        if ip_version == 4:
            if not self.can_do_ipv4:
                self.skipTest("Networking not available")
                return None
            family = socket.AF_INET
        elif ip_version == 6:
            if not self.can_do_ipv6:
                self.skipTest("IPv6 networking not available")
                return None
            family = socket.AF_INET6
        else:
            raise ValueError, "Bad IP version"
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.connect(sockaddr)
        self.client = NetReaderWritter(sock)
        self.client.start()
        return sock.getsockname()

class InitiatorSelectTestCase(NetworkTestCase):
    """Base class for XMPP initiator streams tests, using the
    `SelectMainLoop`.

    :Ivariables:
        - `stream`: The stream tested (to be created by a test method)
        - `transport`: TCPTransport used by the stream
        - `loop`: the main loop
    :Types:
        - `transport`: `TCPTransport`
        - `loop`: `MainLoop`
    """
    def setUp(self):
        super(InitiatorSelectTestCase, self).setUp()
        self.stream = None
        self.transport = None
        self.loop = None

    def start_transport(self, handlers):
        """Initialize a transport and a main loop with the provided handlers"""
        self.transport = TCPTransport()
        self.make_loop(handlers + [self.transport])

    def connect_transport(self):
        """Start a test server and connect the transport to it."""
        addr, port = self.start_server()
        self.transport.connect(addr, port)

    def make_loop(self, handlers):
        """Return a main loop object for use with this test suite."""
        self.loop = SelectMainLoop(None, handlers)

    def tearDown(self):
        super(InitiatorSelectTestCase, self).tearDown()
        self.loop = None
        self.stream = None
        if self.transport:
            self.transport.close()
        self.transport = None

    def wait(self, timeout = TIMEOUT, expect = None):
        """Wait until the main loop finishes, `timeout` seconds passes
        or current server input matches `expect`."""
        timeout = time.time() + timeout
        while not self.loop.finished:
            self.loop.loop_iteration(0.1)
            if expect:
                match = expect.match(self.server.rdata)
                if match:
                    return match.group(1)
            if time.time() > timeout:
                break

    def wait_short(self, timeout = 0.1):
        """Run a single main loop iteration."""
        self.loop.loop_iteration(timeout)

class InitiatorPollTestMixIn(object):
    """Base class for XMPP initiator streams tests, using the
    `PollMainLoop`"""
    # pylint: disable=R0903
    def make_loop(self, handlers):
        """Return a main loop object for use with this test suite."""
        # pylint: disable=W0201
        self.loop = PollMainLoop(None, handlers)

class InitiatorGLibTestMixIn(object):
    """Base class for XMPP initiator streams tests, using the
    `GLibMainLoop`"""
    # pylint: disable=R0903
    def make_loop(self, handlers):
        """Return a main loop object for use with this test suite."""
        # pylint: disable=W0201,W0404
        from pyxmpp2.mainloop.glib import GLibMainLoop
        self.loop = GLibMainLoop(None, handlers)

class InitiatorThreadedTestMixIn(object):
    """Base class for XMPP initiator streams tests, using the
    `ThreadPool` instead of an asynchronous event loop."""
    def make_loop(self, handlers):
        """Return a main loop object for use with this test suite."""
        # pylint: disable=W0201
        self.loop = ThreadPool(XMPPSettings({"upoll_interval": 0.1}), handlers)

    def connect_transport(self):
        """Start a test server and connect the transport to it."""
        InitiatorSelectTestCase.connect_transport(self)
        self.loop.start()

    def tearDown(self):
        """Tear down the test case object."""
        if self.loop:
            logger.debug("Stopping the thread pool")
            try:
                self.loop.stop(True, 2)
            except Exception: # pylint: disable=W0703
                logger.exception("self.loop.stop failed:")
            else:
                logger.debug("  done (or timed out)")
            self.loop.event_dispatcher.flush(False)
        super(InitiatorThreadedTestMixIn, self).tearDown()

class ReceiverSelectTestCase(NetworkTestCase):
    """Base class for XMPP receiver streams tests, using the
    `SelectMainLoop`"""
    def setUp(self):
        super(ReceiverSelectTestCase, self).setUp()
        self.stream = None
        self.transport = None
        self.loop = None
        self.addr = None

    def start_transport(self, handlers):
        """Create a listening socket for the tested stream,
        a transport a main loop and create a client connectiong to the
        socket."""
        sock = self.make_listening_socket()
        self.addr = sock.getsockname()
        self.start_client(self.addr)
        self.transport = TCPTransport(sock = sock.accept()[0])
        sock.close()
        self.make_loop(handlers + [self.transport])

    def make_loop(self, handlers):
        """Create the main loop object."""
        self.loop = SelectMainLoop(None, handlers)

    def wait(self, timeout = TIMEOUT, expect = None):
        """Wait until the main loop finishes, `timeout` seconds passes
        or current server input matches `expect`."""
        timeout = time.time() + timeout
        while not self.loop.finished:
            self.loop.loop_iteration(0.1)
            if expect:
                match = expect.match(self.client.rdata)
                if match:
                    return match.group(1)
            if time.time() > timeout:
                break

    def wait_short(self, timeout = 0.1):
        """Run a single main loop iteration."""
        self.loop.loop_iteration(timeout)

    def tearDown(self):
        self.loop = None
        self.stream = None
        if self.transport:
            self.transport.close()
        self.transport = None
        super(ReceiverSelectTestCase, self).tearDown()

class ReceiverPollTestMixIn(object):
    """Base class for XMPP receiver streams tests, using the
    `PollMainLoop`"""
    # pylint: disable=R0903
    def make_loop(self, handlers):
        """Return a main loop object for use with this test suite."""
        # pylint: disable=W0201
        self.loop = PollMainLoop(None, handlers)

class ReceiverGLibTestMixIn(object):
    """Base class for XMPP receiver streams tests, using the
    `GLibMainLoop`"""
    # pylint: disable=R0903
    def make_loop(self, handlers):
        """Return a main loop object for use with this test suite."""
        # pylint: disable=W0201,W0404
        from pyxmpp2.mainloop.glib import GLibMainLoop
        self.loop = GLibMainLoop(None, handlers)

class ReceiverThreadedTestMixIn(object):
    """Base class for XMPP receiver streams tests, using the
    `ThreadPool`"""
    def make_loop(self, handlers):
        """Return a main loop object for use with this test suite."""
        # pylint: disable=W0201
        self.loop = ThreadPool(XMPPSettings({"upoll_interval": 0.1}), handlers)

    def start_transport(self, handlers):
        """Create a listening socket for the tested stream,
        a transport a main loop and create a client connectiong to the
        socket."""
        super(ReceiverThreadedTestMixIn, self).start_transport(handlers)
        self.loop.start()

    def tearDown(self):
        """Tear down the test case object."""
        if self.loop:
            logger.debug("Stopping the thread pool")
            try:
                self.loop.stop(True, 2)
            except Exception: # pylint: disable=W0703
                logger.exception("self.loop.stop failed:")
            else:
                logger.debug("  done (or timed out)")
            self.loop.event_dispatcher.flush(False)
        super(ReceiverThreadedTestMixIn, self).tearDown()

class EventRecorder(EventHandler):
    """An event handler which records all events received and aborts the main
    loop on the `DisconnectedEvent`.

    :Ivariables:
        - `events_received`: events received
    :Types:
        - `events_received`: `list` of `Event`
    """
    def __init__(self):
        self.events_received = []
    @event_handler()
    def handle_event(self, event):
        """Handle any event: store it in `events_received`."""
        self.events_received.append(event)
        return False
    @event_handler(DisconnectedEvent)
    def handle_disconnected_event(self, event):
        """Handle the `DisconnectedEvent`: abort the main loop."""
        # pylint: disable=R0201
        event.stream.event(QUIT)

