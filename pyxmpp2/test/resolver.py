#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import unittest
import logging
import time

from socket import AF_INET, AF_INET6

try:
    import dns # pylint: disable=W0611
    HAVE_DNSPYTHON = True
except ImportError:
    HAVE_DNSPYTHON = False

from pyxmpp2.mainloop import main_loop_factory
from pyxmpp2.mainloop.interfaces import Event

from pyxmpp2.resolver import is_ipv6_available
from pyxmpp2.resolver import DumbBlockingResolver

if HAVE_DNSPYTHON:
    from pyxmpp2.resolver import BlockingResolver
    from pyxmpp2.resolver import ThreadedResolver

from pyxmpp2.settings import XMPPSettings

from pyxmpp2.test import _support

logger = logging.getLogger("pyxmpp2.test.resolver")

class _Const(object):
    # pylint: disable=R0903
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name
    def __repr__(self):
        return self.name

NO_RESULT = _Const("NO_RESULT")
DUPLICATE = _Const("DUPLICATE")

class DummyEvent(Event):
    # pylint: disable=W0232,R0903
    def __unicode__(self):
        return u"Dummy event"

class _TestResolver(unittest.TestCase):
    def setUp(self):
        # pylint: disable=W0212
        # reset the event queue
        XMPPSettings._defs['event_queue'].default = None
        self.loop = main_loop_factory([])
        self.srv_result = NO_RESULT
        self.address_result = NO_RESULT
        self.wake_up = False

    def wait(self, timeout = 1):
        timeout = time.time() + timeout
        while not self.loop.finished and not self.wake_up:
            self.loop.loop_iteration(0.1)
            if time.time() > timeout:
                break
        self.wake_up = False

    def tearDown(self):
        self.loop.quit()

    def make_resolver(self, settings = None):
        raise NotImplementedError

    def srv_callback(self, result):
        logger.debug("srv_callback: {0!r}".format(result))
        if self.srv_result is not NO_RESULT:
            logger.debug("duplicate call to the srv lookup callback")
            self.srv_result = DUPLICATE
        else:
            self.srv_result = result
        self.wake_up = True
        self.loop.event_queue.put(DummyEvent()) # wake up the main loop

    def address_callback(self, result):
        logger.debug("address_callback: {0!r}".format(result))
        if self.address_result is not NO_RESULT:
            logger.debug("duplicate call to the address lookup callback")
            self.address_result = DUPLICATE
        else:
            self.address_result = result
        self.wake_up = True
        self.loop.event_queue.put(DummyEvent()) # wake up the main loop

    def many_addresses_callback(self, result):
        logger.debug("many_addresses_callback: {0!r}".format(result))
        if self.address_result is NO_RESULT:
            self.address_result = [result]
        else:
            self.address_result.append(result)
        self.wake_up = True
        self.loop.event_queue.put(DummyEvent()) # wake up the main loop

    def test_resolve_srv(self):
        resolver = self.make_resolver()
        self.loop.add_handler(resolver)
        resolver.resolve_srv("lo.test.pyxmpp.jajcus.net",
                                "xmpp-client", "tcp", self.srv_callback)
        self.wait(1)
        self.assertEqual(self.srv_result,
                                [('lo-host.test.pyxmpp.jajcus.net.', 15222)])

    def test_resolve_address(self):
        resolver = self.make_resolver()
        self.loop.add_handler(resolver)
        resolver.resolve_address("lo-host.test.pyxmpp.jajcus.net",
                                                        self.address_callback)
        self.wait(1)
        if is_ipv6_available():
            self.assertEqual(self.address_result, [
                                        (AF_INET6, "::1"),
                                        (AF_INET,  "127.0.0.1")])
        else:
            self.assertEqual(self.address_result, [(AF_INET, "127.0.0.1")])

    def test_resolve_address_prefer_ipv4(self):
        settings = XMPPSettings({"prefer_ipv6": False})
        resolver = self.make_resolver(settings)
        self.loop.add_handler(resolver)
        resolver.resolve_address("lo-host.test.pyxmpp.jajcus.net",
                                                        self.address_callback)
        self.wait(1)
        if is_ipv6_available():
            self.assertEqual(self.address_result, [
                                        (AF_INET,  "127.0.0.1"),
                                        (AF_INET6, "::1")])
        else:
            self.assertEqual(self.address_result, [(AF_INET, "127.0.0.1")])


    def test_resolve_address_ipv4_only(self):
        settings = XMPPSettings({"ipv6": False})
        resolver = self.make_resolver(settings)
        self.loop.add_handler(resolver)
        resolver.resolve_address("lo-host.test.pyxmpp.jajcus.net",
                                                        self.address_callback)
        self.wait(1)
        self.assertEqual(self.address_result, [(AF_INET, "127.0.0.1")])
        self.address_result = NO_RESULT
        resolver.resolve_address("lo4-host.test.pyxmpp.jajcus.net",
                                                        self.address_callback)
        self.wait(1)
        self.assertEqual(self.address_result, [(AF_INET, "127.0.0.1")])
        self.address_result = NO_RESULT
        resolver.resolve_address("lo6-host.test.pyxmpp.jajcus.net",
                                                        self.address_callback)
        self.wait(1)
        self.assertEqual(self.address_result, [])

    @unittest.skipUnless(is_ipv6_available(), "No IPv6 support")
    def test_resolve_address_ipv6_only(self):
        settings = XMPPSettings({"ipv4": False})
        resolver = self.make_resolver(settings)
        self.loop.add_handler(resolver)
        resolver.resolve_address("lo-host.test.pyxmpp.jajcus.net",
                                                        self.address_callback)
        self.wait(1)
        self.assertEqual(self.address_result, [(AF_INET6, "::1")])
        self.address_result = NO_RESULT
        resolver.resolve_address("lo4-host.test.pyxmpp.jajcus.net",
                                                        self.address_callback)
        self.wait(1)
        self.assertEqual(self.address_result, [])
        self.address_result = NO_RESULT
        resolver.resolve_address("lo6-host.test.pyxmpp.jajcus.net",
                                                        self.address_callback)
        self.wait(1)
        self.assertEqual(self.address_result, [(AF_INET6, "::1")])

    def test_resolve_many_addresses(self):
        resolver = self.make_resolver()
        self.loop.add_handler(resolver)
        addresses = ["lo-host", "lo4-host", "lo6-host"]
        addresses += ["nohost{0}".format(i) for i in range(0, 20)]
        addresses = [addr + ".test.pyxmpp.jajcus.net" for addr in addresses]
        for addr in addresses:
            resolver.resolve_address(addr, self.many_addresses_callback)
        timeout = time.time() + 120
        while time.time() < timeout:
            self.wait(1)
            if self.address_result != NO_RESULT and \
                    len(self.address_result) >= len(addresses):
                break
        self.assertEqual(len(self.address_result), len(addresses))
        expected = [[]] * 20
        if is_ipv6_available():
            expected += [[(AF_INET, '127.0.0.1')], [(AF_INET6, '::1')],
                                [(AF_INET6, '::1'), (AF_INET, '127.0.0.1')]]
        else:
            expected += [[], [(AF_INET, '127.0.0.1')], [(2, '127.0.0.1')]]
        results = sorted(self.address_result)
        self.assertEqual(results, expected)

class _TestDumbResolver(_TestResolver):
    def make_resolver(self, settings = None):
        # pylint: disable=E0602
        return DumbResolver(settings)
    def test_resolve_srv(self):
        resolver = self.make_resolver()
        self.loop.add_handler(resolver)
        with self.assertRaises(NotImplementedError):
            resolver.resolve_srv("lo.test.pyxmpp.jajcus.net",
                                "xmpp-client", "tcp", self.srv_callback)
        self.wait(1)
        self.assertEqual(self.srv_result, NO_RESULT)

@unittest.skipUnless("network" in _support.RESOURCES, "network usage disabled")
@unittest.skipUnless(HAVE_DNSPYTHON, "DNSPython not available")
class TestBlockingResolver(_TestResolver):
    def wait(self, timeout = 1):
        return

    def make_resolver(self, settings = None):
        return BlockingResolver(settings)

@unittest.skipUnless("network" in _support.RESOURCES, "network usage disabled")
class TestDumbBlockingResolver(_TestDumbResolver):
    def wait(self, timeout = 1):
        return

    def make_resolver(self, settings = None):
        return DumbBlockingResolver(settings)

@unittest.skipUnless("network" in _support.RESOURCES, "network usage disabled")
@unittest.skipUnless(HAVE_DNSPYTHON, "DNSPython not available")
class TestThreadedResolver(_TestResolver):
    def make_resolver(self, settings = None):
        return ThreadedResolver(settings, 10)

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()

