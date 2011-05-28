#!/usr/bin/python -u
# -*- coding: UTF-8 -*-

import subprocess
import unittest
import binascii

from pyxmpp2 import sasl
    
import logging

logger = logging.getLogger("pyxmpp2.tests.sasl_gsasl")

COMPATIBLE_GSASL = [
            "gsasl (GNU SASL) 1.6.1",
            "gsasl (GNU SASL) 1.6.0",
            ]

gsasl_available = False
gsasl_client_mechanisms = []
gsasl_server_mechanisms = []

def check_gsasl():
    global gsasl_available
    global gsasl_client_mechanisms
    global gsasl_server_mechanisms
    try:
        pipe = subprocess.Popen(["gsasl", "--version"], 
                                    stdout = subprocess.PIPE)
        stdout, stderr = pipe.communicate()
        rc = pipe.wait()
    except OSError:
        rc = -1
    if rc:
        return
    version = stdout.split("\n",1)[0].strip()
    if version not in COMPATIBLE_GSASL:
        logger.debug("GSASL version '{0}' not known to be compatible"
                                                            .format(version))
        return
    try:
        pipe = subprocess.Popen(["gsasl", "--client-mechanisms", 
                    "--quiet"], stdout = subprocess.PIPE, 
                                    stdin = subprocess.PIPE)
        pipe.stdin.write("NjY=")
        pipe.stdin.close()
        stdout = pipe.stdout.readline()
        if "Enter base64" in stdout:
            stdout = pipe.stdout.readline()
        rc = pipe.wait()
    except OSError:
        rc = -1
    if rc:
        return
    gsasl_available = True
    gsasl_client_mechanisms = stdout.split()
    try:
        pipe = subprocess.Popen(["gsasl", "--server-mechanisms", 
                        "--service=xmpp", "--host=pyxmpp.jajcus.net",
                        "--quiet"], stdout = subprocess.PIPE,
                        stdin = subprocess.PIPE)
        pipe.stdin.write("NjY=")
        pipe.stdin.close()
        stdout = pipe.stdout.readline()
        rc = pipe.wait()
    except OSError:
        rc = -1
    if not rc:
        gsasl_server_mechanisms = stdout.split()

class PasswordManager(sasl.PasswordManager):
    def __init__(self, username, password, realms = None):
        self.username = username
        self.password = password
        if realms:
            self.realms = realms
        else:
            self.realms = []
    def get_password(self, username, realm = None, 
                                        acceptable_formats = ("plain",)):
        if self.username == username:
            return self.password, "plain"
        else:
            return None, None
    
    def check_authzid(self, authzid, extra_info=None):
        return not authzid or authzid == 'good_authzid'
    
    def get_realms(self):
        return self.realms
    
    def get_serv_type(self):
        return "xmpp"
    
    def get_serv_host(self):
        return "test.pyxmpp.jajcus.net"
    
    def get_serv_name(self):
        return "pyxmpp.jajcus.net"

class GSASLError(Exception):
    pass

class OurSASLError(Exception):
    pass

class TestSASLClientvsGSASL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not gsasl_available:
            raise unittest.SkipTest("GSASL utility not available")

    def test_PLAIN_good_pass_no_authzid(self):
        if "PLAIN" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no PLAIN support")
        pm = PasswordManager("username", "good")
        authenticator = sasl.client_authenticator_factory("PLAIN", pm)
        ok = self.try_with_gsasl("PLAIN", authenticator)
        self.assertTrue(ok)

    def test_PLAIN_good_pass_authzid(self):
        if "PLAIN" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no PLAIN support")
        pm = PasswordManager("username", "good")
        authenticator = sasl.client_authenticator_factory("PLAIN", pm)
        ok = self.try_with_gsasl("PLAIN", authenticator, authzid = "zid")
        self.assertTrue(ok)

    def test_PLAIN_bad_pass_no_authzid(self):
        if "PLAIN" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no PLAIN support")
        pm = PasswordManager("username", "bad")
        authenticator = sasl.client_authenticator_factory("PLAIN", pm)
        ok = self.try_with_gsasl("PLAIN", authenticator)
        self.assertFalse(ok)

    def test_DIGEST_MD5_good_pass_no_authzid(self):
        if "DIGEST-MD5" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        pm = PasswordManager("username", "good")
        authenticator = sasl.client_authenticator_factory("DIGEST-MD5", pm)
        ok = self.try_with_gsasl("DIGEST-MD5", authenticator, None,
                        ["--service=xmpp", "--realm=jajcus.net",
                         "--host=test.pyxmpp.jajcus.net", 
                         "--service-name=pyxmpp.jajcus.net"])
        self.assertTrue(ok)

    def test_DIGEST_MD5_good_pass_authzid(self):
        if "DIGEST-MD5" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        pm = PasswordManager("username", "good")
        authenticator = sasl.client_authenticator_factory("DIGEST-MD5", pm)
        ok = self.try_with_gsasl("DIGEST-MD5", authenticator, "zid",
                        ["--service=xmpp", "--realm=jajcus.net",
                         "--host=test.pyxmpp.jajcus.net", 
                         "--service-name=pyxmpp.jajcus.net"])
        self.assertTrue(ok)

    def test_DIGEST_MD5_bad_pass_no_authzid(self):
        if "DIGEST-MD5" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        pm = PasswordManager("username", "bad")
        authenticator = sasl.client_authenticator_factory("DIGEST-MD5", pm)
        ok = self.try_with_gsasl("DIGEST-MD5", authenticator, None,
                        ["--service=xmpp", "--realm=jajcus.net",
                         "--host=test.pyxmpp.jajcus.net", 
                         "--service-name=pyxmpp.jajcus.net"])
        self.assertFalse(ok)

    @staticmethod
    def try_with_gsasl(mechanism, authenticator, authzid = None, 
                                                            gsasl_args = []):
        cmd = ["gsasl", "--server", "--quiet",
                "--mechanism=" + mechanism, "--password=good", 
                "-a username"] + gsasl_args
        logger.debug("cmd: %r", " ".join(cmd))
        pipe = subprocess.Popen(cmd, bufsize = 1,
                        stdout = subprocess.PIPE, stdin = subprocess.PIPE,
                                                stderr = open("/dev/null", "w"))
        mech = pipe.stdout.readline().strip()
        logger.debug("IN: %r", mech)
        if mech != mechanism:
            raise GSASLError, "GSASL returned different mechanism: " + mech
        result = authenticator.start("username", authzid)
        if isinstance(result, sasl.Failure):
            raise OurSASLError, result.reason
        response = result.encode()
        if response:
            logger.debug("OUT: %r", response)
            pipe.stdin.write(response + "\n")
        while True:
            challenge = pipe.stdout.readline().strip()
            if not challenge:
                break
            if challenge.startswith('Mechanism requested'):
                continue
            try:
                decoded = challenge.decode("base64")
            except (ValueError, binascii.Error):
                logger.debug("not base64: %r", challenge)
            if challenge.startswith('\x1b[') or response and response.decode("base64") == decoded:
                logger.debug("echo: %r", challenge)
                # for some unknown reason gsasl echoes our data back
                response = None
                continue
            logger.debug("IN: %r", challenge)
            result = authenticator.challenge(decoded)
            if isinstance(result, sasl.Failure):
                raise OurSASLError, result.reason
            response = result.encode()
            logger.debug("OUT: %r", response)
            pipe.stdin.write(response + "\n")
            if response == "":
                break
        pipe.stdin.close()
        pipe.stdout.close()
        rc = pipe.wait()
        if rc:
            return False
        result = authenticator.finish(None)
        return isinstance(result, sasl.Success)

class TestSASLServervsGSASL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not gsasl_available:
            raise unittest.SkipTest("GSASL utility not available")

    def test_PLAIN_good_pass_no_authzid(self):
        if "PLAIN" not in gsasl_client_mechanisms:
            raise unittest.SkipTest("GSASL has no PLAIN support")
        pm = PasswordManager("username", "good")
        authenticator = sasl.server_authenticator_factory("PLAIN", pm)
        ok = self.try_with_gsasl("PLAIN", authenticator)
        self.assertTrue(ok)

    def test_PLAIN_bad_pass_no_authzid(self):
        if "PLAIN" not in gsasl_client_mechanisms:
            raise unittest.SkipTest("GSASL has no PLAIN support")
        pm = PasswordManager("username", "bad")
        authenticator = sasl.server_authenticator_factory("PLAIN", pm)
        with self.assertRaises(OurSASLError) as err:
            self.try_with_gsasl("PLAIN", authenticator)
        self.assertEqual(err.exception.args[0], "not-authorized")

    def test_DIGEST_MD5_good_pass_authzid(self):
        if "DIGEST-MD5" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        pm = PasswordManager("username", "good")
        authenticator = sasl.server_authenticator_factory("DIGEST-MD5", pm)
        ok = self.try_with_gsasl("DIGEST-MD5", authenticator, 
                            [ "--service=xmpp", "--realm=jajcus.net",
                                "--host=test.pyxmpp.jajcus.net",
                                "--service-name=pyxmpp.jajcus.net",
                                "--quality-of-protection=qop-auth"])
        self.assertTrue(ok)

    def test_DIGEST_MD5_bad_pass_no_authzid(self):
        if "DIGEST-MD5" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        pm = PasswordManager("username", "bad")
        authenticator = sasl.server_authenticator_factory("DIGEST-MD5", pm)
        with self.assertRaises(OurSASLError) as err:
            self.try_with_gsasl("DIGEST-MD5", authenticator,
                            [ "--service=xmpp", "--realm=jajcus.net",
                                "--host=test.pyxmpp.jajcus.net",
                                "--service-name=pyxmpp.jajcus.net",
                                "--quality-of-protection=qop-auth"])
        self.assertEqual(err.exception.args[0], "not-authorized")

    @staticmethod
    def try_with_gsasl(mechanism, authenticator, gsasl_args = []):
        cmd = ["gsasl", "--client", "--quiet",
                "--mechanism=" + mechanism, "--password=good",
                "--authentication-id=username"] + gsasl_args
        logger.debug("cmd: %r", " ".join(cmd))
        pipe = subprocess.Popen(cmd, bufsize = 1,
                        stdout = subprocess.PIPE, stdin = subprocess.PIPE,
                                                stderr = open("/dev/null", "w"))
        mech = pipe.stdout.readline().strip()
        logger.debug("IN: %r", mech)
        if mech != mechanism:
            raise GSASLError, "GSASL returned different mechanism: " + mech
        data = pipe.stdout.readline().strip()
        if data:
            result = authenticator.start(data.decode("base64"))
        else:
            result = authenticator.start(None)
        if isinstance(result, sasl.Failure):
            raise OurSASLError, result.reason
        if isinstance(result, sasl.Success):
            pipe.stdin.close()
            pipe.stdout.close()
            rc = pipe.wait()
            if rc:
                raise GSASLError, "GSASL exited with {0}".format(rc)
            return True
        challenge = result.encode()
        logger.debug("OUT: %r", challenge)
        pipe.stdin.write(challenge + "\n")
        while True:
            response = pipe.stdout.readline().strip()
            if not response:
                break
            if response.startswith('Mechanism requested'):
                continue
            try:
                decoded = response.decode("base64")
            except (ValueError, binascii.Error):
                logger.debug("not base64: %r", response)
            if response.startswith('\x1b[') or challenge and challenge.decode("base64") == decoded:
                logger.debug("echo: %r", challenge)
                # for some unknown reason gsasl echoes our data back
                challenge = None
                continue
            logger.debug("IN: %r", response)
            result = authenticator.response(decoded)
            if isinstance(result, sasl.Failure):
                raise OurSASLError, result.reason
            if isinstance(result, sasl.Success):
                break
            challenge = result.encode()
            logger.debug("OUT: %r", challenge)
            pipe.stdin.write(challenge + "\n")
        pipe.stdin.close()
        pipe.stdout.close()
        rc = pipe.wait()
        if rc:
            raise GSASLError, "GSASL exited with {0}".format(rc)
        return authenticator.done

def suite():
    check_gsasl()
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSASLClientvsGSASL))
    suite.addTest(unittest.makeSuite(TestSASLServervsGSASL))
    return suite

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.ERROR)
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
