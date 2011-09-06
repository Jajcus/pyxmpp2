#!/usr/bin/python
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

"""Tests for pyxmpp2.cert"""

import os
import unittest
import socket
import ssl
import threading
import logging

from datetime import datetime

from pyxmpp2.test import _support

from pyxmpp2.jid import JID

from pyxmpp2.cert import HAVE_PYASN1
from pyxmpp2.cert import get_certificate_from_ssl_socket
from pyxmpp2.cert import get_certificate_from_file
from pyxmpp2.cert import ASN1CertificateData, BasicCertificateData

logger = logging.getLogger("pyxmpp2.test.cert")

def socket_with_cert(cert_path, key_path, cacert_path, server_cert = True):
    cert_path = os.path.join(_support.DATA_DIR, cert_path)
    key_path = os.path.join(_support.DATA_DIR, key_path)
    cacert_path = os.path.join(_support.DATA_DIR, cacert_path)
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.bind(("127.0.0.1", 0))
    listen_sock.listen(1)
    addr = listen_sock.getsockname()
    def thread_func():
        try:
            sock, addr = listen_sock.accept()
            sock.setblocking(True)
            try:
                ssl_sock = ssl.wrap_socket(sock, key_path, cert_path,
                             server_side = server_cert, ca_certs = cacert_path)
            finally:
                sock.close()
        finally:
            listen_sock.close()
    thread = threading.Thread(target = thread_func, 
                        name = "pyxmpp2.test.cert certificate provider thread")
    thread.daemon = True
    thread.start()
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(addr)
    if server_cert:
        return ssl.wrap_socket(client_sock, cert_reqs = ssl.CERT_REQUIRED,
                        server_side = False, ca_certs = cacert_path)
    else:
        s_cert_path = os.path.join(_support.DATA_DIR, "server.pem")
        s_key_path = os.path.join(_support.DATA_DIR, "server-key.pem")
        return ssl.wrap_socket(client_sock, s_key_path, s_cert_path,
                        cert_reqs = ssl.CERT_REQUIRED, server_side = True,
                                                    ca_certs = cacert_path)
    
class TestCertFunctions(unittest.TestCase):
    @unittest.skipUnless("lo-network" in _support.RESOURCES, 
                                        "network usage disabled")
    def test_get_certificate_from_ssl_socket(self):
        socket = socket_with_cert("server.pem", "server-key.pem", "ca.pem")
        cert = get_certificate_from_ssl_socket(socket)
        self.assertIsNotNone(cert)
        if HAVE_PYASN1:
            self.assertIsInstance(cert, ASN1CertificateData)
        else:
            self.assertIsInstance(cert, BasicCertificateData)
        self.assertTrue(cert.validated)
        self.assertTrue("server.example.org" in cert.common_names)
    
    @unittest.skipUnless(HAVE_PYASN1, "No pyasn1")
    def test_get_server_certificate_from_file(self):
        cert_path = os.path.join(_support.DATA_DIR, "server.pem")
        cert = get_certificate_from_file(cert_path)
        self.assertIsNotNone(cert)
        self.assertIsInstance(cert, ASN1CertificateData)
        self.assertFalse(cert.validated)
        self.assertTrue("server.example.org" in cert.common_names)
 
    @unittest.skipUnless(HAVE_PYASN1, "No pyasn1")
    def test_get_client_certificate_from_file(self):
        cert_path = os.path.join(_support.DATA_DIR, "client.pem")
        cert = get_certificate_from_file(cert_path)
        self.assertIsNotNone(cert)
        self.assertIsInstance(cert, ASN1CertificateData)
        self.assertFalse(cert.validated)
        self.assertTrue("user@server.example.org" in cert.alt_names["XmppAddr"])

class TestBasicCertificateData(unittest.TestCase):
    @staticmethod
    def load_certificate(name, server_cert = True):
        cert_file = name + ".pem"
        key_file = name + "-key.pem"
        socket = socket_with_cert(cert_file, key_file, "ca.pem", server_cert)
        return BasicCertificateData.from_ssl_socket(socket)

    def test_server_cert_fields(self):
        cert = self.load_certificate("server", True)
        self.assertEqual(cert.subject_name, (
                                (('organizationName', u'PyXMPP'),),
                                (('organizationalUnitName', u'Unit Tests'),),
                                (('commonName', u'server.example.org'),)
                                            ))
        self.assertIsInstance(cert.not_after, datetime)
        self.assertGreater(cert.not_after, datetime.now())
        self.assertEqual(list(cert.common_names), [u"server.example.org"])
        self.assertEqual(list(cert.alt_names["DNS"]), [u"server.example.org"])
        if not isinstance(cert, BasicCertificateData):
            self.assertEqual(list(cert.alt_names["SRVName"]),
                                        [u"_xmpp-server.server.example.org"])
        self.assertEqual(cert.display_name, u"organizationName=PyXMPP, "
                            u"organizationalUnitName=Unit Tests, "
                            u"commonName=server.example.org")
        self.assertEqual(cert.get_jids(), [JID("server.example.org")])

    def test_client_cert_fields(self):
        cert = self.load_certificate("client", False)
        self.assertEqual(cert.subject_name, (
                                (('organizationName', u'PyXMPP'),),
                                (('organizationalUnitName', u'Unit Tests'),),
                                (('commonName', u'Client Name'),)
                                            ))
        self.assertIsInstance(cert.not_after, datetime)
        self.assertGreater(cert.not_after, datetime.now())
        self.assertEqual(list(cert.common_names), [u"Client Name"])
        self.assertFalse(cert.alt_names.get("DNS"))
        self.assertFalse(cert.alt_names.get("SRVName"))
        if not isinstance(cert, BasicCertificateData):
            self.assertEqual(list(cert.alt_names["XmppAddr"]),
                                        [u"user@server.example.org"])
        self.assertEqual(cert.display_name, u"organizationName=PyXMPP, "
                            u"organizationalUnitName=Unit Tests, "
                            u"commonName=Client Name")
        if not isinstance(cert, BasicCertificateData):
            self.assertEqual(cert.get_jids(), [JID("user@server.example.org")])

    def test_server1_cert_fields(self):
        cert = self.load_certificate("server1", True)
        self.assertEqual(cert.subject_name, (
                                (('organizationName', u'PyXMPP'),),
                                (('organizationalUnitName', u'Unit Tests'),),
                                (('commonName', u'common-name.example.org'),)
                                            ))
        self.assertIsInstance(cert.not_after, datetime)
        self.assertGreater(cert.not_after, datetime.now())
        self.assertEqual(list(cert.common_names), [u"common-name.example.org"])
        self.assertEqual(list(cert.alt_names["DNS"]), 
                                [u"dns1.example.org", u"dns2.example.org",
                                    u"*.wild.example.org"])
        if not isinstance(cert, BasicCertificateData):
            self.assertEqual(list(cert.alt_names["SRVName"]),
                                    [u"_xmpp-server.srv1.example.org",
                                        u"_xmpp-server.srv2.example.org"])
            self.assertEqual(list(cert.alt_names["XmppAddr"]),
                                    [u"xmppaddr1.example.org",
                                        u"xmppaddr2.example.org"])
        self.assertEqual(cert.display_name, u"organizationName=PyXMPP, "
                            u"organizationalUnitName=Unit Tests, "
                            u"commonName=common-name.example.org")
        jids = [JID("dns1.example.org"), JID("dns2.example.org")]
        if not isinstance(cert, BasicCertificateData):
            jids += [
                    JID("srv1.example.org"), JID("srv2.example.org"),
                    JID("xmppaddr1.example.org"), JID("xmppaddr2.example.org")]
        self.assertEqual(set(cert.get_jids()), set(jids))

    def test_client1_cert_fields(self):
        cert = self.load_certificate("client1", False)
        self.assertEqual(cert.subject_name, (
                                (('organizationName', u'PyXMPP'),),
                                (('organizationalUnitName', u'Unit Tests'),),
                                (('commonName', u'common-name@example.org'),)
                                            ))
        self.assertIsInstance(cert.not_after, datetime)
        self.assertGreater(cert.not_after, datetime.now())
        self.assertEqual(list(cert.common_names), [u"common-name@example.org"])
        self.assertFalse(cert.alt_names.get("DNS"))
        self.assertFalse(cert.alt_names.get("SRVName"))
        if not isinstance(cert, BasicCertificateData):
            self.assertEqual(list(cert.alt_names["XmppAddr"]),
                            [u"user1@server.example.org",
                                            u"user2@server.example.org"])
        self.assertEqual(cert.display_name, u"organizationName=PyXMPP, "
                            u"organizationalUnitName=Unit Tests, "
                            u"commonName=common-name@example.org")
        if not isinstance(cert, BasicCertificateData):
            self.assertEqual(cert.get_jids(), [JID("user1@server.example.org"),
                                            JID("user2@server.example.org")])


@unittest.skipUnless(HAVE_PYASN1, "No pyasn1")
class TestASN1CertificateData(TestBasicCertificateData):
    @staticmethod
    def load_certificate(name, server_cert = True):
        cert_file = os.path.join(_support.DATA_DIR, name + ".pem")
        return ASN1CertificateData.from_file(cert_file)
 
# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
