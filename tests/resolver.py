#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import logging
import time

from socket import AF_INET, AF_INET6

from pyxmpp2.mainloop import main_loop_factory
from pyxmpp2.mainloop.interfaces import Event

from pyxmpp2.resolver import is_ipv6_available
from pyxmpp2.resolver import DumbBlockingResolver, BlockingResolver
from pyxmpp2.resolver import ThreadedResolver
from pyxmpp2.settings import XMPPSettings

NO_RESULT = object()
DUPLICATE = object()

class DummyEvent(Event):
    def __unicode__(self):
        return u"Dummy event"

class TestResolver(unittest.TestCase):
    def setUp(self):
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
        self.loop = None

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
            expected += [[(2, '127.0.0.1')], [(10, '::1')], [(10, '::1'), (2, '127.0.0.1')]]
        else:
            expected += [[], [(2, '127.0.0.1')], [(2, '127.0.0.1')]]
        results = sorted(self.address_result)
        self.assertEqual(results, expected)

class TestDumbResolver(TestResolver):
    def test_resolve_srv(self):
        resolver = self.make_resolver()
        self.loop.add_handler(resolver)
        with self.assertRaises(NotImplementedError):
            resolver.resolve_srv("lo.test.pyxmpp.jajcus.net",
                                "xmpp-client", "tcp", self.srv_callback)
        self.wait(1)
        self.assertEqual(self.srv_result, NO_RESULT)

class TestBlockingResolver(TestResolver):
    def wait(self, timeout):
        return

    def make_resolver(self, settings = None):
        return BlockingResolver(settings)

class TestDumbBlockingResolver(TestBlockingResolver, TestDumbResolver):
    def make_resolver(self, settings = None):
        return DumbBlockingResolver(settings)

class TestThreadedResolver(TestResolver):
    def make_resolver(self, settings = None):
        return ThreadedResolver(settings, 10)


def suite():
     suite = unittest.TestSuite()
     #suite.addTest(unittest.makeSuite(TestDumbBlockingResolver))
     #suite.addTest(unittest.makeSuite(TestBlockingResolver))
     suite.addTest(unittest.makeSuite(TestThreadedResolver))
     return suite

if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.ERROR)
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
