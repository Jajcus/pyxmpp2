#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest

import pyxmpp.interface
import pyxmpp.interface_micro_impl

try:
    import zope.interface
    zope_interface_found = True
except ImportError:
    zope_interface_found = False

class TestInterface(unittest.TestCase):
    interfaces_implementation = None

    def test_interface_definitions(self):
        class I1(self.interfaces_implementation.Interface):
            pass
        class I2(self.interfaces_implementation.Interface):
            a = self.interfaces_implementation.Attribute("some attribute")
        class I3(self.interfaces_implementation.Interface):
            def f(arg1, arg2):
                """some funtion"""
        class I3(self.interfaces_implementation.Interface):
            a = self.interfaces_implementation.Attribute("some attribute")
            def f(arg1, arg2):
                """some funtion"""

    def test_implementedBy(self):
        class I1(self.interfaces_implementation.Interface):
            pass
        class I2(self.interfaces_implementation.Interface):
            pass
        class C1(object):
            self.interfaces_implementation.implements(I1)
        class C2(object):
            self.interfaces_implementation.implements(I2)
        self.failUnless(I1.implementedBy(C1))
        self.failUnless(I2.implementedBy(C2))
        self.failIf(I2.implementedBy(C1))
        self.failIf(I1.implementedBy(C2))

    def test_providedBy(self):
        class I1(self.interfaces_implementation.Interface):
            pass
        class I2(self.interfaces_implementation.Interface):
            pass
        class C1(object):
            self.interfaces_implementation.implements(I1)
        class C2(object):
            self.interfaces_implementation.implements(I2)
        o1=C1()
        o2=C2()
        self.failUnless(I1.providedBy(o1))
        self.failUnless(I2.providedBy(o2))
        self.failIf(I2.providedBy(o1))
        self.failIf(I1.providedBy(o2))

    def test_inheritance(self):
        class I1(self.interfaces_implementation.Interface):
            pass
        class I2(I1):
            pass
        class C1(object):
            self.interfaces_implementation.implements(I2)
        o1 = C1()
        self.failUnless(I1.providedBy(o1))
        self.failUnless(issubclass(I2, I1))

class TestPyXMPPInterface(TestInterface):
    interfaces_implementation = pyxmpp.interface

class TestPyXMPPMicroInterface(TestInterface):
    interfaces_implementation = pyxmpp.interface_micro_impl

if zope_interface_found:
    class TestZopeInterface(TestInterface):
        interfaces_implementation = zope.interface

class TestZopeAndPyXMPPInterface(unittest.TestCase):
    def test_interface_identity(self):
        self.failUnless(pyxmpp.interface.Interface is zope.interface.Interface)
    def test_attribute_identity(self):
        self.failUnless(pyxmpp.interface.Attribute is zope.interface.Attribute)
    def test_implements_identity(self):
        self.failUnless(pyxmpp.interface.implements is zope.interface.implements)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPyXMPPInterface))
    suite.addTest(unittest.makeSuite(TestPyXMPPMicroInterface))
    if zope_interface_found:
        suite.addTest(unittest.makeSuite(TestZopeInterface))
        suite.addTest(unittest.makeSuite(TestZopeAndPyXMPPInterface))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
