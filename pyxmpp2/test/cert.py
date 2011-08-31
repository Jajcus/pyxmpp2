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

from pyxmpp2.test import _support

from pyxmpp2.cert import HAVE_PYASN1
from pyxmpp2.cert import get_certificate_from_ssl_socket
from pyxmpp2.cert import get_certificate_from_file
from pyxmpp2.cert import ASN1CertificateData, BasicCertificateData

logger = logging.getLogger("pyxmpp2.test.cert")

def socket_with_cert(cert_path, key_path, cacert_path):
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
            try:
                ssl_sock = ssl.wrap_socket(sock, key_path, cert_path,
                                            True, ca_certs = cacert_path)
            finally:
                sock.close()
        finally:
            listen_sock.close()
    thread = threading.Thread(target = thread_func)
    thread.daemon = True
    thread.start()
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(addr)
    return ssl.wrap_socket(client_sock, cert_reqs = ssl.CERT_REQUIRED,
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
 
# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    setup_logging()

if __name__ == "__main__":
    unittest.main()
