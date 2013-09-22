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
            sock = listen_sock.accept()[0]
            sock.setblocking(True) # pylint: disable=E1101
            try:
                ssl.wrap_socket(sock, key_path, cert_path,
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
        sock = socket_with_cert("server.pem", "server-key.pem", "ca.pem")
        cert = get_certificate_from_ssl_socket(sock)
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
        sock = socket_with_cert(cert_file, key_file, "ca.pem", server_cert)
        return BasicCertificateData.from_ssl_socket(sock)

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

    def test_verify_server(self):
        cert = self.load_certificate("server", True)
        self.assertTrue(cert.verify_server(u"server.example.org"))
        self.assertTrue(cert.verify_server(JID(u"server.example.org")))
        self.assertFalse(cert.verify_server(u"wrong.example.org"))
        self.assertFalse(cert.verify_server(JID(u"wrong.example.org")))
        self.assertFalse(cert.verify_server(u"example.org"))
        self.assertFalse(cert.verify_server(u"sub.server.example.org"))


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
                                    [u"_xmpp-client.client-srv.example.org",
                                        u"_xmpp-server.server-srv.example.org"])
            self.assertEqual(list(cert.alt_names["XmppAddr"]),
                                    [u"xmppaddr1.example.org",
                                        u"xmppaddr2.example.org"])
        self.assertEqual(cert.display_name, u"organizationName=PyXMPP, "
                            u"organizationalUnitName=Unit Tests, "
                            u"commonName=common-name.example.org")
        jids = [JID("dns1.example.org"), JID("dns2.example.org")]
        if not isinstance(cert, BasicCertificateData):
            jids += [ JID("client-srv.example.org"),
                    JID("server-srv.example.org"),
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

    def test_verify_server1_wrong(self):
        cert = self.load_certificate("server1", True)
        self.assertFalse(cert.verify_server(u"common-name.example.org"))
        self.assertFalse(cert.verify_server(u"example.org"))
        self.assertFalse(cert.verify_server(u"bad.example.org"))
        self.assertFalse(cert.verify_server(u"wild.example.org"))
        self.assertFalse(cert.verify_server(u"sub.sub.wild.example.org"))
        self.assertFalse(cert.verify_server(u"client-srv.example.org",
                                                                "xmpp-server"))
        self.assertFalse(cert.verify_server(u"server-srv.example.org"))
        self.assertFalse(cert.verify_server(u"server-srv.example.org",
                                                                "xmpp-client"))

    def test_verify_server1_dns(self):
        cert = self.load_certificate("server1", True)
        self.assertTrue(cert.verify_server(u"dns1.example.org"))
        self.assertTrue(cert.verify_server(u"dns2.example.org"))

@unittest.skipUnless(HAVE_PYASN1, "No pyasn1")
class TestASN1CertificateData(TestBasicCertificateData):
    @staticmethod
    def load_certificate(name, server_cert = True):
        cert_file = os.path.join(_support.DATA_DIR, name + ".pem")
        return ASN1CertificateData.from_file(cert_file)

    def test_verify_server1_srv(self):
        cert = self.load_certificate("server1", True)
        self.assertTrue(cert.verify_server(u"client-srv.example.org"))
        self.assertTrue(cert.verify_server(u"client-srv.example.org",
                                                                "xmpp-client"))
        self.assertTrue(cert.verify_server(u"server-srv.example.org",
                                                                "xmpp-server"))

    def test_verify_server1_xmppaddr(self):
        cert = self.load_certificate("server1", True)
        self.assertTrue(cert.verify_server(u"xmppaddr1.example.org"))
        self.assertTrue(cert.verify_server(u"xmppaddr2.example.org"))

    def test_verify_server1_wildcard(self):
        cert = self.load_certificate("server1", True)
        self.assertTrue(cert.verify_server(u"sub.wild.example.org"))
        self.assertTrue(cert.verify_server(u"somethinelse.wild.example.org"))

    def test_verify_client(self):
        cert = self.load_certificate("client", False)
        self.assertEqual(cert.verify_client(), JID("user@server.example.org"))
        self.assertEqual(cert.verify_client(JID("user@server.example.org")),
                                               JID("user@server.example.org"))
        self.assertEqual(cert.verify_client(JID("other@server.example.org")),
                                               JID("user@server.example.org"))
        self.assertEqual(cert.verify_client(domains = ["server.example.org"]),
                                               JID("user@server.example.org"))
        self.assertIsNone(cert.verify_client(domains = ["bad.example.org"]))

        cert = self.load_certificate("server", True)
        self.assertIsNone(cert.verify_client())

    def test_verify_client1(self):
        cert = self.load_certificate("client1", False)
        self.assertEqual(cert.verify_client(), JID("user1@server.example.org"))
        self.assertEqual(cert.verify_client(JID("user1@server.example.org")),
                                               JID("user1@server.example.org"))
        self.assertEqual(cert.verify_client(JID("user2@server.example.org")),
                                               JID("user2@server.example.org"))
        self.assertEqual(cert.verify_client(JID("other@server.example.org")),
                                               JID("user1@server.example.org"))
        self.assertEqual(cert.verify_client(domains = ["server.example.org"]),
                                               JID("user1@server.example.org"))
        self.assertIsNone(cert.verify_client(domains = ["bad.example.org"]))

        cert = self.load_certificate("server1", True)
        self.assertIsNone(cert.verify_client())


# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
