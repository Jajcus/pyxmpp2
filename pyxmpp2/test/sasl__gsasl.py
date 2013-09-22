#!/usr/bin/python -u
# -*- coding: UTF-8 -*-
# pylint: disable=C0111

import subprocess
import unittest
import binascii
from binascii import a2b_base64
from base64 import standard_b64encode

from pyxmpp2 import sasl
from pyxmpp2.sasl.core import CLIENT_MECHANISMS_D

from pyxmpp2.test import _support

import logging

logger = logging.getLogger("pyxmpp2.tests.sasl_gsasl")

COMPATIBLE_GSASL = [
            b"gsasl (GNU SASL) 1.6.1",
            b"gsasl (GNU SASL) 1.6.0",
            ]

gsasl_available = False # pylint: disable=C0103
gsasl_client_mechanisms = [] # pylint: disable=C0103
gsasl_server_mechanisms = [] # pylint: disable=C0103

def check_gsasl():
    # pylint: disable=W0603,E1103
    global gsasl_available
    global gsasl_client_mechanisms
    global gsasl_server_mechanisms
    try:
        pipe = subprocess.Popen(["gsasl", "--version"],
                                    stdout = subprocess.PIPE)
        stdout = pipe.communicate()[0]
        code = pipe.wait()
    except OSError:
        code = -1
    if code:
        return
    version = stdout.split(b"\n", 1)[0].strip()
    if version not in COMPATIBLE_GSASL:
        logger.debug("GSASL version '{0}' not known to be compatible"
                                                            .format(version))
        return
    if logger.isEnabledFor(logging.DEBUG):
        quiet = []
    else:
        quiet = ["--quiet"]
    try:
        pipe = subprocess.Popen(["gsasl", "--client-mechanisms"] + quiet,
                            stdout = subprocess.PIPE, stdin = subprocess.PIPE)
        stdout = pipe.communicate(b"NjY=\n")[0]
        stdout = stdout.strip().rsplit(b"\n", 1)[-1]
        code = pipe.wait()
    except OSError:
        code = -1
    if code:
        return
    gsasl_available = True
    gsasl_client_mechanisms = [s for s in stdout.decode("us-ascii").split()]
    logger.debug("client mechanisms: {0!r}".format(gsasl_client_mechanisms))
    try:
        pipe = subprocess.Popen(["gsasl", "--server-mechanisms"] + quiet,
                            stdout = subprocess.PIPE, stdin = subprocess.PIPE)
        stdout = pipe.communicate(b"abcd\n" * 4)[0]
        stdout = stdout.strip().rsplit(b"\n", 1)[-1]
        code = pipe.wait()
    except OSError:
        code = -1
    if not code:
        gsasl_server_mechanisms = [s for s in stdout.decode("us-ascii").split()]
        logger.debug("server mechanisms: {0!r}".format(gsasl_server_mechanisms))

class PasswordDatabase(sasl.PasswordDatabase):
    def __init__(self, username, password, realms = None):
        self.username = username
        self.password = password
        if realms:
            self.realms = realms
        else:
            self.realms = []
    def get_password(self, username, acceptable_formats, properties):
        if self.username == username:
            return self.password, "plain"
        else:
            return None, None

class GSASLError(Exception):
    pass

class OurSASLError(Exception):
    pass

@unittest.skipIf("gsasl" not in _support.RESOURCES, "GSASL usage disabled")
class TestSASLClientvsGSASL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not gsasl_available:
            raise unittest.SkipTest("GSASL utility not available")

    def test_PLAIN_good_pass_no_authzid(self):
        if "PLAIN" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no PLAIN support")
        authenticator = sasl.client_authenticator_factory("PLAIN")
        auth_prop = {
                        "username": u"username",
                        "password": u"good",
                      }
        ok, props = self.try_with_gsasl("PLAIN", authenticator, auth_prop)
        self.assertTrue(ok)
        self.assertFalse(props.get("authzid"))

    def test_PLAIN_good_pass_authzid(self):
        if "PLAIN" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no PLAIN support")
        authenticator = sasl.client_authenticator_factory("PLAIN")
        auth_prop = {
                            "username": u"username",
                            "password": u"good",
                            "authzid": u"zid",
                          }
        ok, props = self.try_with_gsasl("PLAIN", authenticator, auth_prop)
        self.assertTrue(ok)
        self.assertEqual(props.get("authzid"), "zid")

    def test_PLAIN_bad_pass_no_authzid(self):
        if "PLAIN" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no PLAIN support")
        authenticator = sasl.client_authenticator_factory("PLAIN")
        auth_prop = {
                        "username": u"username",
                        "password": u"bad",
                      }
        ok, props = self.try_with_gsasl("PLAIN", authenticator, auth_prop)
        self.assertFalse(ok)
        self.assertFalse(props.get("authzid"))

    def test_DIGEST_MD5_good_pass_no_authzid(self):
        if "DIGEST-MD5" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        authenticator = sasl.client_authenticator_factory("DIGEST-MD5")
        auth_prop = {
                        "username": u"username",
                        "password": u"good",
                        "service-type": u"xmpp",
                        "service-domain": u"pyxmpp.jajcus.net",
                        "service-hostname": u"test.pyxmpp.jajcus.net",
                      }
        ok, props = self.try_with_gsasl("DIGEST-MD5", authenticator, auth_prop,
                        ["--service=xmpp", "--realm=jajcus.net",
                         "--host=test.pyxmpp.jajcus.net",
                         "--service-name=pyxmpp.jajcus.net"])
        self.assertTrue(ok)
        self.assertFalse(props.get("authzid"))

    def test_DIGEST_MD5_good_pass_authzid(self):
        if "DIGEST-MD5" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        authenticator = sasl.client_authenticator_factory("DIGEST-MD5")
        auth_prop = {
                        "username": u"username",
                        "password": u"good",
                        "service-type": u"xmpp",
                        "service-domain": u"pyxmpp.jajcus.net",
                        "service-hostname": u"test.pyxmpp.jajcus.net",
                        "authzid": u"zid",
                      }
        ok, props = self.try_with_gsasl("DIGEST-MD5", authenticator, auth_prop,
                        ["--service=xmpp", "--realm=jajcus.net",
                         "--host=test.pyxmpp.jajcus.net",
                         "--service-name=pyxmpp.jajcus.net"])
        self.assertTrue(ok)
        self.assertEqual(props.get("authzid"), u"zid")

    def test_DIGEST_MD5_bad_pass_no_authzid(self):
        if "DIGEST-MD5" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        authenticator = sasl.client_authenticator_factory("DIGEST-MD5")
        auth_prop = {
                        "username": u"username",
                        "password": u"bad",
                        "service-type": u"xmpp",
                        "service-domain": u"pyxmpp.jajcus.net",
                        "service-hostname": u"test.pyxmpp.jajcus.net",
                      }
        ok, dummy = self.try_with_gsasl("DIGEST-MD5", authenticator, auth_prop,
                        ["--service=xmpp", "--realm=jajcus.net",
                         "--host=test.pyxmpp.jajcus.net",
                         "--service-name=pyxmpp.jajcus.net"])
        self.assertFalse(ok)

    def test_SCRAM_SHA_1_good_pass_no_authzid(self):
        if "SCRAM-SHA-1" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        authenticator = sasl.client_authenticator_factory("SCRAM-SHA-1")
        auth_prop = {
                        "username": u"username",
                        "password": u"good",
                      }
        ok, props = self.try_with_gsasl("SCRAM-SHA-1", authenticator, auth_prop,
                                            ["--no-cb"])
        self.assertTrue(ok)
        self.assertFalse(props.get("authzid"))

    def test_SCRAM_SHA_1_good_pass_authzid(self):
        if "SCRAM-SHA-1" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        authenticator = sasl.client_authenticator_factory("SCRAM-SHA-1")
        auth_prop = {
                        "username": u"username",
                        "password": u"good",
                        "authzid": u"zid",
                      }
        ok, props = self.try_with_gsasl("SCRAM-SHA-1", authenticator, auth_prop,
                                            ["--no-cb"])
        self.assertTrue(ok)
        self.assertEqual(props.get("authzid"), "zid")

    def test_SCRAM_SHA_1_quoting(self):
        if "SCRAM-SHA-1" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        authenticator = sasl.client_authenticator_factory("SCRAM-SHA-1")
        auth_prop = {
                        "username": u"pi=3,14",
                        "password": u"good",
                        "authzid": u"e=2,72",
                      }
        ok, props = self.try_with_gsasl("SCRAM-SHA-1", authenticator, auth_prop,
                                            ["--no-cb"], username = "pi=3,14")
        self.assertTrue(ok)
        self.assertEqual(props.get("authzid"), "e=2,72")

    def test_SCRAM_SHA_1_bad_pass_no_authzid(self):
        if "SCRAM-SHA-1" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        authenticator = sasl.client_authenticator_factory("SCRAM-SHA-1")
        auth_prop = {
                        "username": u"username",
                        "password": u"bad",
                      }
        ok, dummy = self.try_with_gsasl("SCRAM-SHA-1", authenticator, auth_prop,
                                            ["--no-cb"])
        self.assertFalse(ok)

    def test_SCRAM_SHA_1_good_pass_downgrade(self):
        # Check protection from channel-binding downgrade.
        if "SCRAM-SHA-1-PLUS" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        authenticator = sasl.client_authenticator_factory("SCRAM-SHA-1")
        auth_prop = {
                        "enabled_mechanisms": ["SCRAM-SHA-1",
                                                    "SCRAM-SHA-1-PLUS"],
                        "username": u"username",
                        "password": u"good",
                      }
        cb_data = b"0123456789ab"
        ok, dummy = self.try_with_gsasl("SCRAM-SHA-1",
                                    authenticator, auth_prop,
                                    extra_data = standard_b64encode(cb_data))
        self.assertFalse(ok)

    @unittest.skipIf("SCRAM-SHA-1-PLUS" not in CLIENT_MECHANISMS_D,
                        "SCRAM-SHA-1-PLUS not available in PyXMPP2")
    def test_SCRAM_SHA_1_PLUS_good_pw_good_cb(self):
        if "SCRAM-SHA-1-PLUS" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1-PLUS support")
        authenticator = sasl.client_authenticator_factory("SCRAM-SHA-1-PLUS")
        cb_data = b"0123456789ab"
        auth_prop = {
                        "username": u"username",
                        "password": u"good",
                        "channel-binding": {
                            "tls-unique": cb_data,
                        },
                      }
        ok, props = self.try_with_gsasl("SCRAM-SHA-1-PLUS",
                                        authenticator,
                                        auth_prop,
                                    extra_data = standard_b64encode(cb_data))
        self.assertTrue(ok)
        self.assertFalse(props.get("authzid"))

    @unittest.skipIf("SCRAM-SHA-1-PLUS" not in CLIENT_MECHANISMS_D,
                        "SCRAM-SHA-1-PLUS not available in PyXMPP2")
    def test_SCRAM_SHA_1_PLUS_bad_pw_good_cb(self):
        if "SCRAM-SHA-1-PLUS" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1-PLUS support")
        authenticator = sasl.client_authenticator_factory("SCRAM-SHA-1-PLUS")
        cb_data = b"0123456789ab"
        auth_prop = {
                        "username": u"username",
                        "password": u"bad",
                        "channel-binding": {
                            "tls-unique": cb_data,
                        },
                      }
        ok, dummy = self.try_with_gsasl("SCRAM-SHA-1-PLUS",
                                        authenticator,
                                        auth_prop,
                                    extra_data = standard_b64encode(cb_data))
        self.assertFalse(ok)

    @unittest.skipIf("SCRAM-SHA-1-PLUS" not in CLIENT_MECHANISMS_D,
                        "SCRAM-SHA-1-PLUS not available in PyXMPP2")
    def test_SCRAM_SHA_1_PLUS_good_pw_bad_cb(self):
        if "SCRAM-SHA-1-PLUS" not in gsasl_server_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1-PLUS support")
        authenticator = sasl.client_authenticator_factory("SCRAM-SHA-1-PLUS")
        cb_data = b"0123456789ab"
        auth_prop = {
                        "username": u"username",
                        "password": u"good",
                        "channel-binding": {
                            "tls-unique": cb_data,
                        },
                      }
        cb_data = b"BAD_BAD_BAD_"
        ok, dummy = self.try_with_gsasl("SCRAM-SHA-1-PLUS",
                                        authenticator,
                                        auth_prop,
                                    extra_data = standard_b64encode(cb_data))
        self.assertFalse(ok)

    @staticmethod
    def try_with_gsasl(mechanism, authenticator, auth_properties,
                    gsasl_args = [], extra_data = None, username = "username"):
        # pylint: disable=W0102,R0914,R0912,R0915
        cmd = ["gsasl", "--server",
                "--mechanism=" + mechanism, "--password=good",
                "--authentication-id={0}".format(username)] + gsasl_args
        if logger.isEnabledFor(logging.DEBUG):
            stderr = None
            logger.debug("cmd: %r", " ".join(cmd))
        else:
            cmd.append("--quiet")
            stderr = open("/dev/null", "w")
        pipe = subprocess.Popen(cmd, bufsize = 1, stdout = subprocess.PIPE,
                        stdin = subprocess.PIPE, stderr = stderr)
        if stderr:
            stderr.close()
        if extra_data:
            data = extra_data + b"\n"
            logger.debug("OUT: %r", data)
            pipe.stdin.write(data)
            pipe.stdin.flush()
        mech = pipe.stdout.readline()
        logger.debug("IN: %r", mech)
        if extra_data and extra_data in mech:
            mech = pipe.stdout.readline()
            logger.debug("IN: %r", mech)
        mech = mech.strip().decode("utf-8")
        if mech != mechanism:
            pipe.stdin.close()
            pipe.stdout.close()
            raise GSASLError, "GSASL returned different mechanism: " + mech
        result = authenticator.start(auth_properties)
        if isinstance(result, sasl.Failure):
            pipe.stdin.close()
            pipe.stdout.close()
            raise OurSASLError, result.reason
        response = result.encode()
        if response:
            data = (response + "\n").encode("utf-8")
            logger.debug("OUT: %r", data)
            pipe.stdin.write(data)
            pipe.stdin.flush()
            ignore_empty_challenge = True
        else:
            ignore_empty_challenge = False
        while True:
            challenge = pipe.stdout.readline().strip()
            if not challenge:
                if ignore_empty_challenge:
                    logger.debug("Ignoring empty initial challenge")
                    ignore_empty_challenge = False
                    continue
                else:
                    break
            if challenge.startswith(b'Mechanism requested'):
                continue
            try:
                decoded = a2b_base64(challenge)
            except (ValueError, binascii.Error):
                logger.debug("not base64: %r", challenge)
            if challenge.startswith(b'\x1b['):
                logger.debug("echo: %r", challenge)
                # for some unknown reason gsasl echoes our data back
                response = None
                continue
            if response and a2b_base64(response.encode("utf-8")) == decoded:
                logger.debug("echo: %r", challenge)
                # for some unknown reason gsasl echoes our data back
                response = None
                continue
            logger.debug("IN: %r", challenge)
            result = authenticator.challenge(decoded)
            if isinstance(result, sasl.Failure):
                raise OurSASLError, result.reason
            response = result.encode()
            data = (response + "\n").encode("utf-8")
            logger.debug("OUT: %r", data)
            pipe.stdin.write(data)
            pipe.stdin.flush()
            if not response:
                break
        pipe.stdin.close()
        pipe.stdout.close()
        code = pipe.wait()
        if code:
            return False, {}
        result = authenticator.finish(None)
        if isinstance(result, sasl.Success):
            return True, result.properties
        else:
            return False, {}

@unittest.skipIf("gsasl" not in _support.RESOURCES, "GSASL usage disabled")
class TestSASLServervsGSASL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not gsasl_available:
            raise unittest.SkipTest("GSASL utility not available")

    def test_PLAIN_good_pass_no_authzid(self):
        if "PLAIN" not in gsasl_client_mechanisms:
            raise unittest.SkipTest("GSASL has no PLAIN support")
        pwdb = PasswordDatabase("username", "good")
        authenticator = sasl.server_authenticator_factory("PLAIN", pwdb)
        ok, props = self.try_with_gsasl("PLAIN", authenticator, {})
        self.assertTrue(ok)
        self.assertFalse(props.get("authzid"))

    def test_PLAIN_bad_pass_no_authzid(self):
        if "PLAIN" not in gsasl_client_mechanisms:
            raise unittest.SkipTest("GSASL has no PLAIN support")
        pwdb = PasswordDatabase("username", "bad")
        authenticator = sasl.server_authenticator_factory("PLAIN", pwdb)
        with self.assertRaises(OurSASLError) as err:
            self.try_with_gsasl("PLAIN", authenticator, {})
        self.assertEqual(err.exception.args[0], "not-authorized")

    def test_DIGEST_MD5_good_pass_no_authzid(self):
        if "DIGEST-MD5" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        pwdb = PasswordDatabase("username", "good")
        authenticator = sasl.server_authenticator_factory("DIGEST-MD5", pwdb)
        auth_prop = {
                        "service-type": u"xmpp",
                        "service-domain": u"pyxmpp.jajcus.net",
                        "service-hostname": u"test.pyxmpp.jajcus.net",
                      }
        ok, props = self.try_with_gsasl("DIGEST-MD5", authenticator, auth_prop,
                            [ "--service=xmpp", "--realm=jajcus.net",
                                "--host=test.pyxmpp.jajcus.net",
                                "--service-name=pyxmpp.jajcus.net",
                                "--quality-of-protection=qop-auth"])
        self.assertTrue(ok)
        self.assertIsNone(props.get("authzid"))


    def test_DIGEST_MD5_good_pass_authzid(self):
        if "DIGEST-MD5" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        pwdb = PasswordDatabase("username", "good")
        authenticator = sasl.server_authenticator_factory("DIGEST-MD5", pwdb)
        auth_prop = {
                        "service-type": u"xmpp",
                        "service-domain": u"pyxmpp.jajcus.net",
                        "service-hostname": u"test.pyxmpp.jajcus.net",
                      }
        ok, props = self.try_with_gsasl("DIGEST-MD5", authenticator, auth_prop,
                            [ "--service=xmpp", "--realm=jajcus.net",
                                "--host=test.pyxmpp.jajcus.net",
                                "--service-name=pyxmpp.jajcus.net",
                                "--quality-of-protection=qop-auth",
                                "--authorization-id=zid"])
        self.assertTrue(ok)
        self.assertEqual(props.get("authzid"), "zid")

    def test_DIGEST_MD5_bad_pass_no_authzid(self):
        if "DIGEST-MD5" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no DIGEST-MD5 support")
        pwdb = PasswordDatabase("username", "bad")
        authenticator = sasl.server_authenticator_factory("DIGEST-MD5", pwdb)
        auth_prop = {
                        "service-type": u"xmpp",
                        "service-domain": u"pyxmpp.jajcus.net",
                        "service-hostname": u"test.pyxmpp.jajcus.net",
                      }
        with self.assertRaises(OurSASLError) as err:
            self.try_with_gsasl("DIGEST-MD5", authenticator, auth_prop,
                            [ "--service=xmpp", "--realm=jajcus.net",
                                "--host=test.pyxmpp.jajcus.net",
                                "--service-name=pyxmpp.jajcus.net",
                                "--quality-of-protection=qop-auth"])
        self.assertEqual(err.exception.args[0], "not-authorized")

    def test_SCRAM_SHA_1_good_pass_no_authzid(self):
        if "SCRAM-SHA-1" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        pwdb = PasswordDatabase("username", "good")
        authenticator = sasl.server_authenticator_factory("SCRAM-SHA-1", pwdb)
        auth_prop = { "enabled_mechanisms": ["SCRAM-SHA-1"]}
        ok, props = self.try_with_gsasl("SCRAM-SHA-1", authenticator, auth_prop,
                                                        [ "--no-cb"])
        self.assertTrue(ok)
        self.assertIsNone(props.get("authzid"))

    def test_SCRAM_SHA_1_good_pass_authzid(self):
        if "SCRAM-SHA-1" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        pwdb = PasswordDatabase("username", "good")
        authenticator = sasl.server_authenticator_factory("SCRAM-SHA-1", pwdb)
        auth_prop = { }
        ok, props = self.try_with_gsasl("SCRAM-SHA-1", authenticator, auth_prop,
                                        [ "--no-cb", "--authorization-id=zid"])
        self.assertTrue(ok)
        self.assertEqual(props.get("authzid"), "zid")

    def test_SCRAM_SHA_1_quoting(self):
        if "SCRAM-SHA-1" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        pwdb = PasswordDatabase("pi=3,14", "good")
        authenticator = sasl.server_authenticator_factory("SCRAM-SHA-1", pwdb)
        auth_prop = { }
        ok, props = self.try_with_gsasl("SCRAM-SHA-1", authenticator, auth_prop,
                            [ "--no-cb", "--authorization-id=e=2,72"],
                            username = "pi=3,14")
        self.assertTrue(ok)
        self.assertEqual(props.get("authzid"), "e=2,72")


    def test_SCRAM_SHA_1_bad_username(self):
        if "SCRAM-SHA-1" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        pwdb = PasswordDatabase("bad", "good")
        authenticator = sasl.server_authenticator_factory("SCRAM-SHA-1", pwdb)
        auth_prop = { }
        with self.assertRaises(OurSASLError) as err:
            self.try_with_gsasl("SCRAM-SHA-1", authenticator, auth_prop,
                                                                [ "--no-cb"])
        self.assertEqual(err.exception.args[0], "not-authorized")

    def test_SCRAM_SHA_1_bad_pass_no_authzid(self):
        if "SCRAM-SHA-1" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        pwdb = PasswordDatabase("username", "bad")
        authenticator = sasl.server_authenticator_factory("SCRAM-SHA-1", pwdb)
        auth_prop = { }
        with self.assertRaises(OurSASLError) as err:
            self.try_with_gsasl("SCRAM-SHA-1", authenticator,
                                                auth_prop, [ "--no-cb"])
        self.assertEqual(err.exception.args[0], "not-authorized")

    def test_SCRAM_SHA_1_good_pass_downgrade(self):
        if "SCRAM-SHA-1" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1 support")
        pwdb = PasswordDatabase("username", "good")
        authenticator = sasl.server_authenticator_factory("SCRAM-SHA-1", pwdb)
        auth_prop = { "enabled_mechanisms": ["SCRAM-SHA-1", "SCRAM-SHA-1-PLUS"]}
        cb_data = b"0123456789ab"
        with self.assertRaises(OurSASLError) as err:
            self.try_with_gsasl("SCRAM-SHA-1", authenticator, auth_prop,
                                    extra_data = standard_b64encode(cb_data))
        self.assertEqual(err.exception.args[0], "not-authorized")

    def test_SCRAM_SHA_1_PLUS_good_pass_authzid(self):
        if "SCRAM-SHA-1-PLUS" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1-PLUS support")
        pwdb = PasswordDatabase("username", "good")
        authenticator = sasl.server_authenticator_factory("SCRAM-SHA-1-PLUS",
                                                                        pwdb)
        cb_data = b"0123456789ab"
        auth_prop = { "channel-binding": {"tls-unique": cb_data} }
        ok, props = self.try_with_gsasl("SCRAM-SHA-1-PLUS", authenticator,
                                        auth_prop, ["--authorization-id=zid"],
                                    extra_data = standard_b64encode(cb_data))
        self.assertTrue(ok)
        self.assertEqual(props.get("authzid"), "zid")

    def test_SCRAM_SHA_1_PLUS_bad_pass_no_authzid(self):
        if "SCRAM-SHA-1-PLUS" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1-PLUS support")
        pwdb = PasswordDatabase("username", "bad")
        authenticator = sasl.server_authenticator_factory("SCRAM-SHA-1-PLUS",
                                                                        pwdb)
        cb_data = b"0123456789ab"
        auth_prop = { "channel-binding": {"tls-unique": cb_data} }
        with self.assertRaises(OurSASLError) as err:
            self.try_with_gsasl("SCRAM-SHA-1-PLUS", authenticator, auth_prop,
                                    extra_data = standard_b64encode(cb_data))
        self.assertEqual(err.exception.args[0], "not-authorized")

    def test_SCRAM_SHA_1_PLUS_good_pass_bad_cb(self):
        if "SCRAM-SHA-1-PLUS" not in gsasl_client_mechanisms:
            raise unittest.SkipTest( "GSASL has no SCRAM-SHA-1-PLUS support")
        pwdb = PasswordDatabase("username", "good")
        authenticator = sasl.server_authenticator_factory("SCRAM-SHA-1-PLUS",
                                                                        pwdb)
        cb_data = b"0123456789ab"
        auth_prop = { "channel-binding": {"tls-unique": cb_data} }
        bad_cb_data = b"ab0123456789"
        with self.assertRaises(OurSASLError) as err:
            self.try_with_gsasl("SCRAM-SHA-1-PLUS", authenticator, auth_prop,
                                extra_data = standard_b64encode(bad_cb_data))
        self.assertEqual(err.exception.args[0], "not-authorized")



    @staticmethod
    def try_with_gsasl(mechanism, authenticator, auth_prop, gsasl_args = [],
                                    extra_data = None, username = "username"):
        # pylint: disable=W0102,R0914,R0912,R0915
        cmd = ["gsasl", "--client",
                "--mechanism=" + mechanism, "--password=good",
                "--authentication-id={0}".format(username)] + gsasl_args
        if logger.isEnabledFor(logging.DEBUG):
            stderr = None
            logger.debug("cmd: %r", " ".join(cmd))
        else:
            cmd.append("--quiet")
            stderr = open("/dev/null", "w")
        pipe = subprocess.Popen(cmd, bufsize = 1, stdout = subprocess.PIPE,
                                    stdin = subprocess.PIPE, stderr = stderr)
        if stderr:
            stderr.close()
        if extra_data:
            data = extra_data + b"\n"
            logger.debug("OUT: %r", data)
            pipe.stdin.write(data)
            pipe.stdin.flush()
        mech = pipe.stdout.readline()
        logger.debug("IN: %r", mech)
        if extra_data and extra_data in mech:
            mech = pipe.stdout.readline()
            logger.debug("IN: %r", mech)
        mech = mech.strip().decode("utf-8")
        logger.debug("IN: %r", mech)
        if mech != mechanism:
            raise GSASLError, "GSASL returned different mechanism: " + mech
        data = pipe.stdout.readline().strip()
        if data:
            result = authenticator.start(auth_prop, a2b_base64(data))
        else:
            result = authenticator.start(auth_prop, None)
        if isinstance(result, sasl.Failure):
            pipe.stdin.close()
            pipe.stdout.close()
            raise OurSASLError, result.reason
        if isinstance(result, sasl.Success):
            pipe.stdin.close()
            pipe.stdout.close()
            code = pipe.wait()
            if code:
                raise GSASLError, "GSASL exited with {0}".format(code)
            return True, result.properties
        challenge = result.encode()
        data = (challenge + "\n").encode("utf-8")
        logger.debug("OUT: %r", data)
        pipe.stdin.write(data)
        pipe.stdin.flush()
        success = None
        while not success:
            response = pipe.stdout.readline().strip()
            if not response:
                break
            if response.startswith(b'Mechanism requested'):
                continue
            try:
                decoded = a2b_base64(response)
            except (ValueError, binascii.Error):
                logger.debug("not base64: %r", response)
            if response.startswith(b'\x1b[') or challenge and (
                    a2b_base64(challenge.encode("utf-8")) == decoded):
                logger.debug("echo: %r", challenge)
                # for some unknown reason gsasl echoes our data back
                challenge = None
                continue
            logger.debug("IN: %r", response)
            result = authenticator.response(decoded)
            if isinstance(result, sasl.Failure):
                pipe.stdin.close()
                pipe.stdout.close()
                raise OurSASLError, result.reason
            if isinstance(result, sasl.Success):
                success = result
                if not success.data:
                    break
            challenge = result.encode()
            data = (challenge + "\n").encode("utf-8")
            logger.debug("OUT: %r", data)
            pipe.stdin.write(data)
            pipe.stdin.flush()
        pipe.communicate()
        pipe.stdin.close()
        pipe.stdout.close()
        code = pipe.wait()
        if code:
            raise GSASLError, "GSASL exited with {0}".format(code)
        if success:
            return True, success.properties
        else:
            return False, None

# pylint: disable=W0611
from pyxmpp2.test._support import load_tests, setup_logging

def setUpModule():
    check_gsasl()
    setup_logging()

if __name__ == "__main__":
    unittest.main()
