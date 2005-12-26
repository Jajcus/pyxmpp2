#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import libxml2
import threading

from pyxmpp.cache import Cache,CacheSuite,CacheFetcher,CacheItem
from datetime import timedelta,datetime
from time import sleep

class TestClass1:
    def __init__(self,adr):
        self.adr=adr
    def __repr__(self):
        return "<TestClass1 %r>" % (self.adr,)
    def __cmp__(self,other):
        return cmp((self.adr, self.__class__),(other.adr, other.__class__))

class TestClass2:
    def __init__(self,adr):
        self.adr=adr
    def __repr__(self):
        return "<TestClass2 %r>" % (self.adr,)
    def __cmp__(self,other):
        return cmp((self.adr, self.__class__),(other.adr, other.__class__))

def sec(x):
    return timedelta(seconds=x)

class TestCacheItem(unittest.TestCase):
    def test_item(self):
        pre = datetime.utcnow()
        o = TestClass1("test_addr")
        item = CacheItem("test_addr",o, sec(0.1), sec(0.2), sec(0.3))
        post = datetime.utcnow()

        self.failUnless(item.timestamp >= pre and item.timestamp <= post)
        self.failUnless(item.value is o)
        self.failUnless(item.address == "test_addr")

    def test_item_state_transitions(self):
        item = CacheItem("test_addr","test_value", sec(0.1), sec(0.2), sec(0.3))

        # t+0
        self.failUnlessEqual(item.state,"new")
        state = item.update_state()
        self.failUnlessEqual(state,item.state)
        self.failUnlessEqual(item.state,"fresh")

        sleep(0.01)
        # t+~0.01
        state = item.update_state()
        self.failUnlessEqual(state,item.state)
        self.failUnlessEqual(item.state,"fresh")

        sleep(0.1)
        # t+~0.11
        state = item.update_state()
        self.failUnlessEqual(state,item.state)
        self.failUnlessEqual(item.state,"old")

        sleep(0.01)
        # t+~0.12
        state = item.update_state()
        self.failUnlessEqual(state,item.state)
        self.failUnlessEqual(item.state,"old")

        sleep(0.1)
        # t+~0.22
        state = item.update_state()
        self.failUnlessEqual(state,item.state)
        self.failUnlessEqual(item.state,"stale")

        sleep(0.01)
        # t+~0.23
        state = item.update_state()
        self.failUnlessEqual(state,item.state)
        self.failUnlessEqual(item.state,"stale")

        sleep(0.1)
        # t+~0.33
        state = item.update_state()
        self.failUnlessEqual(state,item.state)
        self.failUnlessEqual(item.state,"purged")

        sleep(0.1)
        # t+~0.43
        state = item.update_state()
        self.failUnlessEqual(state,item.state)
        self.failUnlessEqual(item.state,"purged")

class TestCacheFetcher(unittest.TestCase):
    def setUp(self):
        self.cache = Cache(100)
        self.event = None

    def make_fetcher(self):
        return CacheFetcher(self.cache, "test_addr", sec(1), sec(2), sec(3),
                self.object_handler, self.error_handler, self.timeout_handler,
                sec(1))

    def object_handler(self, address, value, state):
        self.event = ("success", address, value, state)

    def error_handler(self, address, error_data):
        self.event = ("error", address, error_data)

    def timeout_handler(self, address):
        self.event = ("timeout", address)

    def test_fetcher_fetch(self):
        fetcher = self.make_fetcher()
        self.failUnlessRaises(RuntimeError,fetcher.fetch)

    def test_success(self):
        fetcher = self.make_fetcher()
        fetcher.got_it("test_value")
        self.failUnlessEqual(self.event,("success", "test_addr", "test_value", "new"))
        self.event = None
        fetcher.got_it("test_value")
        self.failUnlessEqual(self.event, None)

    def test_success_other_state(self):
        fetcher = self.make_fetcher()
        fetcher.got_it("test_value","stale")
        self.failUnlessEqual(self.event,("success", "test_addr", "test_value", "stale"))

    def test_error(self):
        fetcher = self.make_fetcher()
        fetcher.error("test_error")
        self.failUnlessEqual(self.event,("error", "test_addr", "test_error"))
        self.event = None
        fetcher.error("test_error")
        self.failUnlessEqual(self.event, None)

    def test_timeout(self):
        fetcher = self.make_fetcher()
        fetcher.timeout()
        self.failUnlessEqual(self.event,("timeout", "test_addr"))
        self.event = None
        fetcher.timeout()
        self.failUnlessEqual(self.event, None)

class TestCache(unittest.TestCase):
    def setUp(self):
        self.event = None
        self.force_error = False
        fetcher_owner = self
        class MyFetcher(CacheFetcher):
            owner = fetcher_owner
            def fetch(self):
                thread = threading.Thread(target=self.thread)
                thread.start()
            def thread(self):
                sleep(0.2)
                if self.owner.force_error:
                    self.error("Forced error")
                elif self.address >= 0:
                    self.got_it("value%i" % (self.address,))
                else:
                    self.error("Negative address")
        self.Fetcher = MyFetcher

    def test_add_get_item(self):
        cache = Cache(100)
        item1 = CacheItem("test_addr1","test_value1", sec(1), sec(2), sec(3))
        cache.add_item(item1)
        item2 = CacheItem("test_addr2","test_value2", sec(1), sec(2), sec(3))
        cache.add_item(item2)
        item3 = CacheItem("test_addr3","test_value3", sec(1), sec(2), sec(3))
        cache.add_item(item3)
        gitem2 = cache.get_item("test_addr2","fresh")
        self.failUnless(gitem2 is item2, "gitem2=%r item2=%r" % (gitem2, item2))
        gitem1 = cache.get_item("test_addr1","old")
        self.failUnless(gitem1 is item1, "gitem2=%r item2=%r" % (gitem2, item2))
        gitem3 = cache.get_item("test_addr3","stale")
        self.failUnless(gitem3 is item3, "gitem2=%r item2=%r" % (gitem2, item2))
        gitem1 = cache.get_item("test_addr1","new")
        self.failUnless(gitem1 is None, "gitem1=%r" % (gitem1,))

    def test_max_items(self):
        cache = Cache(10)
        self.failUnlessEqual(cache.num_items(),0,"number of items: "+`cache.num_items()`)
        for i in range(10):
            item = CacheItem(i,i, sec(1), sec(2), sec(3))
            cache.add_item(item)
        self.failUnlessEqual(cache.num_items(),10,"number of items: "+`cache.num_items()`)
        for i in range(10,30):
            item = CacheItem(i,i, sec(1), sec(2), sec(3))
            cache.add_item(item)
        self.failUnless(cache.num_items() > 7,"number of items: "+`cache.num_items()`)
        self.failUnless(cache.num_items() <= 10,"number of items: "+`cache.num_items()`)
        self.failUnlessEqual(cache.num_items(),len(cache._items),
            "number of items: %r, in dict: %r" % (cache.num_items(), cache._items))

    def test_item_expiration(self):
        cache = Cache(100)
        item = CacheItem("test_addr","test_value", sec(0.1), sec(0.2), sec(0.3))
        cache.add_item(item)
        gitem = cache.get_item("test_addr","fresh")
        self.failUnlessEqual(gitem,item)
        sleep(0.01)
        gitem = cache.get_item("test_addr","fresh")
        self.failUnlessEqual(gitem,item)
        sleep(0.1)
        gitem = cache.get_item("test_addr","fresh")
        self.failUnlessEqual(gitem,None)
        cache.tick()
        gitem = cache.get_item("test_addr","old")
        self.failUnlessEqual(gitem,item)
        sleep(0.3)
        cache.tick()
        gitem = cache.get_item("test_addr","stale")
        self.failUnlessEqual(gitem,None)
        self.failUnlessEqual(cache.num_items(),0,"number of items: "+`cache.num_items()`)

    def test_request_object_success(self):
        cache = Cache(100)
        cache.set_fetcher(self.Fetcher)
        cache.request_object(1, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.3)
        self.failUnlessEqual(self.event,("success", 1, "value1", "new"))
        self.event = None
        cache.request_object(1, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,("success", 1, "value1", "fresh"))
        self.event = None
        cache.request_object(2, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        cache.tick()
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.3)
        cache.tick()
        self.failUnlessEqual(self.event,("success", 2, "value2", "new"))
        self.event = None
        cache.request_object(2, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,("success", 2, "value2", "fresh"))
        cache.tick()
        self.event = None
        cache.request_object(1, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,("success", 1, "value1", "fresh"))

    def test_request_object_backup(self):
        cache = Cache(100)
        cache.set_fetcher(self.Fetcher)
        cache.request_object(1, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.3)
        self.failUnlessEqual(self.event,("success", 1, "value1", "new"))
        self.event = None
        self.force_error = True
        cache.request_object(1, "new", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.3)
        self.failUnlessEqual(self.event,("error", 1, "Forced error"))
        self.event = None

        self.force_error = True
        cache.request_object(1, "new", self.object_handler,
                self.error_handler, self.timeout_handler,
                backup_state = "stale")
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.3)
        self.failUnlessEqual(self.event,("success", 1, "value1", "stale"))

    def test_request_object_failure(self):
        cache = Cache(100)
        cache.set_fetcher(self.Fetcher)
        cache.request_object(-1, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        cache.tick()
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.3)
        cache.tick()
        self.failUnlessEqual(self.event,("error", -1, "Negative address"))

    def test_request_object_timeout(self):
        cache = Cache(100)
        cache.set_fetcher(self.Fetcher)
        cache.request_object(1, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler,
                timeout=timedelta(seconds=0.1))
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        cache.tick()
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        cache.tick()
        sleep(0.05)
        cache.tick()
        sleep(0.05)
        cache.tick()
        sleep(0.3)
        cache.tick()
        self.failUnlessEqual(self.event,("timeout", 1))

    def object_handler(self, address, value, state):
        self.event = ("success", address, value, state)

    def error_handler(self, address, error_data):
        self.event = ("error", address, error_data)

    def timeout_handler(self, address):
        self.event = ("timeout", address)

class TestCacheSuite(unittest.TestCase):
    def setUp(self):
        self.event = None
        self.force_error = False
        fetcher_owner = self
        class MyFetcher(CacheFetcher):
            cls = None
            owner = fetcher_owner
            def fetch(self):
                thread = threading.Thread(target=self.thread)
                thread.start()
            def thread(self):
                sleep(0.2)
                if self.owner.force_error:
                    self.error("Forced error")
                elif self.address >= 0:
                    self.got_it(self.cls(self.address))
                else:
                    self.error("Negative address")

        class MyFetcher1(MyFetcher):
            cls = TestClass1

        class MyFetcher2(MyFetcher):
            cls = TestClass2

        self.Fetcher1 = MyFetcher1
        self.Fetcher2 = MyFetcher2

    def test_request_object_success(self):
        cache = CacheSuite(100)
        cache.register_fetcher(TestClass1, self.Fetcher1)
        cache.register_fetcher(TestClass2, self.Fetcher2)

        cache.request_object(TestClass1, 1, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.3)
        self.failUnlessEqual(self.event,("success", 1, TestClass1(1), "new"))
        self.event = None
        cache.request_object(TestClass1, 1, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,("success", 1, TestClass1(1), "fresh"))
        self.event = None
        cache.request_object(TestClass2, 2, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.05)
        cache.tick()
        self.failUnlessEqual(self.event,None,"Early event: %r" % (self.event,))
        sleep(0.3)
        cache.tick()
        self.failUnlessEqual(self.event,("success", 2, TestClass2(2), "new"))
        self.event = None
        cache.request_object(TestClass2, 2, "fresh", self.object_handler,
                self.error_handler, self.timeout_handler)
        self.failUnlessEqual(self.event,("success", 2, TestClass2(2), "fresh"))

    def object_handler(self, address, value, state):
        self.event = ("success", address, value, state)

    def error_handler(self, address, error_data):
        self.event = ("error", address, error_data)

    def timeout_handler(self, address):
        self.event = ("timeout", address)


def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestCacheItem))
     suite.addTest(unittest.makeSuite(TestCacheFetcher))
     suite.addTest(unittest.makeSuite(TestCache))
     suite.addTest(unittest.makeSuite(TestCacheSuite))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
