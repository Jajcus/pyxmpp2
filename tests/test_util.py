"""Utilities for pyxmmp2 unit tests."""

import unittest
import socket
import threading
import select
import logging
import ssl

logger = logging.getLogger("pyxmpp.test.test_util")

socket.setdefaulttimeout(5)

class NetReaderWritter(object):
    def __init__(self, sock, need_accept = False):
        self.sock = sock
        self.reader = None
        self.writter = None
        self.wdata = ""
        self.rdata = ""
        self.eof = False
        self.error = False
        self.ready = not need_accept
        self.write_enabled = True
        self.lock = threading.RLock()
        self.write_cond = threading.Condition(self.lock)
        self.eof_cond = threading.Condition(self.lock)
        self.extra_on_read = None

    def start(self):
        reader_thread = threading.Thread(target = self.reader_run, 
                                                            name = "Reader")
        reader_thread.daemon = True
        writter_thread = threading.Thread(target = self.writter_run, 
                                                            name = "Writter")
        writter_thread.daemon = True
        reader_thread.start()
        writter_thread.start()

    def do_tls_handshake(self):
        logger.debug(" starting tls handshake")
        self.sock.do_handshake()
        logger.debug(" tls handshake started, resuming normal write")
        self.extra_on_read = None
        self.write_enabled = True
        self.write_cond.notify()

    def starttls(self, *args, **kwargs):
        kwargs['do_handshake_on_connect'] = False
        with self.lock:
            # flush write buffer
            logger.debug(" flushing write buffer before tls wrap")
            while self.wdata:
                self.write_cond.wait()
            self.write_enabled = False
            self.write_cond.notify()
            logger.debug(" wrapping the socket")
            self.sock = ssl.wrap_socket(*args, **kwargs)
            self.extra_on_read = self.do_tls_handshake

    def writter_run(self):
        with self.write_cond:
            while self.sock is not None:
                while self.ready and self.wdata and self.write_enabled:
                    sent = self.sock.send(self.wdata)
                    logger.debug(u"tst OUT: " + repr(self.wdata[:sent]))
                    self.wdata = self.wdata[sent:]
                    self.write_cond.notify()
                self.write_cond.wait()

    def reader_run(self):
        with self.lock:
            poll = select.poll()
            poll.register(self.sock, select.POLLIN | select.POLLERR 
                                                        | select.POLLHUP)
            while not self.eof and self.sock is not None:
                self.lock.release()
                try:
                    ret = poll.poll(5)
                finally:
                    self.lock.acquire()
                if not self.sock:
                    break
                for fd, event in ret:
                    if event & select.POLLIN:
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
                            poll.unregister(self.sock)
                            self.sock.close()
                            self.sock = sock1
                            poll.register(self.sock, select.POLLIN 
                                            | select.POLLERR | select.POLLHUP)
                            self.ready = True
                            self.write_cond.notify()
                            break
                    if event & (select.POLLERR | select.POLLHUP):
                        self.sock = None
                        self.error = True
                        self.eof_cond.notifyAll()
                        break

    def write(self, data):
        with self.write_cond:
            self.wdata += data
            if self.ready:
                self.write_cond.notify()

    def read(self):
        with self.cond:
            data, self.rdata = self.rdata, ""
        return data

    def close(self):
        with self.lock:
            if self.sock is not None:
                self.sock.close()
            self.sock = None
            self.wdata = None
            self.write_cond.notify()
            self.eof_cond.wait(0.1)

    def wait(self, timeout):
        with self.eof_cond:
            if not self.eof and not self.error:
                self.eof_cond.wait(timeout)

class NetworkTestCase(unittest.TestCase):
    can_do_ipv4 = False
    can_do_ipv6 = False
    @classmethod
    def setUpClass(cls):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock1.connect(sock.getsockname())
            sock.accept()
            sock1.close()
            sock.close()
            cls.can_do_ipv4 = True
        except socket.error:
            pass
        if socket.has_ipv6:
            try:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.bind(("::1", 0))
                sock.listen(1)
                sock1 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock1.connect(sock.getsockname())
                sock.accept()
                sock1.close()
                sock.close()
                cls.can_do_ipv6 = True
            except socket.error:
                pass

    def setUp(self):
        self.server = None
        self.client = None

    def tearDown(self):
        if self.server:
            self.server.close()
        if self.client:
            self.client.close()

    def start_server(self, ip_version = 4):
        sock = self.make_listening_socket(ip_version)
        self.server = NetReaderWritter(sock, need_accept = True)
        self.server.start()
        return sock.getsockname()
    
    def make_listening_socket(self, ip_version = 4):
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
