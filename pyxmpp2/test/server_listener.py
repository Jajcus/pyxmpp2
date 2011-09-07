#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

"""Tests for pyxmpp2.server.listener"""

import unittest
import socket
import threading
import logging
import time
import select

try:
    import glib
except ImportError:
    # pylint: disable=C0103
    glib = None

from pyxmpp2.test import _support

from pyxmpp2.server.listener import TCPListener
from pyxmpp2.mainloop.select import SelectMainLoop
from pyxmpp2.mainloop.poll import PollMainLoop
from pyxmpp2.mainloop.threads import ThreadPool

logger = logging.getLogger("pyxmpp2.test.server_listener")

TEST_PORT = 10256
TIMEOUT = 30 # seconds

@unittest.skipIf("lo-network" not in _support.RESOURCES,
                                        "loopback network usage disabled")
class TestListenerSelect(unittest.TestCase):
    def setUp(self):
        self.lock = threading.RLock()
        self.connected = []
        self.accepted = []

    @staticmethod
    def make_loop(handlers):
        """Return a main loop object for use with this test suite."""
        return SelectMainLoop(None, handlers)

    def tearDown(self):
        with self.lock:
            for sock in self.connected:
                sock.close()
            for sock, _addr in self.accepted:
                sock.close()
            self.connected = None
            self.accepted = None

    def start_connections(self, target_address, number):
        """
        Start a thread which will make `number` connections to
        `target_address`.
        """
        def thread_func():
            for dummy in range(number):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock.connect(target_address)
                    with self.lock:
                        if self.connected is None:
                            return
                        self.connected.append(sock)
                except:
                    sock.close()
                    raise
        thread = threading.Thread(name = "Listener test connections",
                                                    target = thread_func)
        thread.daemon = True
        thread.start()

    def accept(self, sock, address):
        with self.lock:
            if self.accepted is None:
                return
            self.accepted.append((sock, address))

    def test_listener(self):
        listener = TCPListener(socket.AF_INET, ('127.0.0.1', TEST_PORT), 
                                                                self.accept)
        loop = self.make_loop([listener])
        loop.loop_iteration(0.1)
        self.start_connections(('127.0.0.1', TEST_PORT), 10)
        timeout = time.time() + TIMEOUT
        while not loop.finished and (len(self.accepted) < 10
                                                or len(self.connected) < 10):
            loop.loop_iteration(0.1)
            if time.time() > timeout:
                break
        listener.close()
        self.assertEqual(len(self.accepted), 10)
        self.assertEqual(len(self.connected), 10)
        con_addrs = [sock.getsockname() for sock in self.connected]
        con_addrs.sort()
        acc_addrs = [acc[1] for acc in self.accepted]
        acc_addrs.sort()
        self.assertEqual(con_addrs, acc_addrs)
        self.assertEqual(self.accepted[0][0].getpeername(),
                                                        self.accepted[0][1])

@unittest.skipIf("lo-network" not in _support.RESOURCES,
                                        "loopback network usage disabled")
@unittest.skipIf(not hasattr(select, "poll"), "No poll() support")
class TestListenerPoll(TestListenerSelect):
    @staticmethod
    def make_loop(handlers):
        """Return a main loop object for use with this test suite."""
        return PollMainLoop(None, handlers)

@unittest.skip("Broken-slow")
@unittest.skipIf("lo-network" not in _support.RESOURCES,
                                        "loopback network usage disabled")
@unittest.skipIf(glib is None, "No glib module")
class TestListenerGLib(TestListenerSelect):
    @staticmethod
    def make_loop(handlers):
        """Return a main loop object for use with this test suite."""
        from pyxmpp2.mainloop.glib import GLibMainLoop
        return GLibMainLoop(None, handlers)

@unittest.skipIf("lo-network" not in _support.RESOURCES,
                                        "loopback network usage disabled")
@unittest.skipIf(not hasattr(select, "poll"), "No poll() support")
class TestListenerThread(TestListenerSelect):
    def setUp(self):
        self._loop = None
        super(TestListenerThread, self).setUp()
    def make_loop(self, handlers):
        """Return a main loop object for use with this test suite."""
        self._loop = ThreadPool(None, handlers)
        self._loop.start()
        return self._loop
    def tearDown(self):
        if self._loop:
            logger.debug("Stopping the thread pool")
            try:
                self._loop.stop(True, 2)
            except Exception: # pylint: disable=W0703
                logger.exception("self.loop.stop failed:")
            else:
                logger.debug("  done (or timed out)")
            self._loop.event_dispatcher.flush(False)
        super(TestListenerThread, self).tearDown()

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
