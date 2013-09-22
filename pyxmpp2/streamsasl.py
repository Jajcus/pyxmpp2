#
# (C) Copyright 2003-2011 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# pylint: disable-msg=W0201

"""SASL support XMPP streams.

Normative reference:
  - `RFC 6120 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import logging
from binascii import a2b_base64

from .etree import ElementTree, element_to_unicode
from .jid import JID
from . import sasl
from .exceptions import SASLNotAvailable, FatalStreamError
from .exceptions import SASLMechanismNotAvailable, SASLAuthenticationFailed
from .constants import SASL_QNP
from .settings import XMPPSettings
from .interfaces import StreamFeatureHandler
from .interfaces import StreamFeatureHandled, StreamFeatureNotHandled
from .interfaces import stream_element_handler

logger = logging.getLogger("pyxmpp2.streamsasl")

class DefaultPasswordDatabase(sasl.PasswordDatabase):
    """Default password database.

    Uses the :r:`user_passwords setting` or :r:`username setting`
    and :r:`password setting`.
    """
    def __init__(self, settings):
        self.settings = settings

    def get_password(self, username, acceptable_formats, properties):
        if "plain" not in acceptable_formats:
            return None, None

        if "user_passwords" in self.settings:
            pwd_map = self.settings["user_passwords"]
            if username in pwd_map:
                return pwd_map[username], "plain"
            else:
                return None, None
        if "username" in self.settings and "password" in self.settings:
            return self.settings["password"], "plain"
        else:
            return None, None


MECHANISMS_TAG = SASL_QNP + u"mechanisms"
MECHANISM_TAG = SASL_QNP + u"mechanism"
CHALLENGE_TAG = SASL_QNP + u"challenge"
SUCCESS_TAG = SASL_QNP + u"success"
FAILURE_TAG = SASL_QNP + u"failure"
AUTH_TAG = SASL_QNP + u"auth"
RESPONSE_TAG = SASL_QNP + u"response"
ABORT_TAG = SASL_QNP + u"abort"

class StreamSASLHandler(StreamFeatureHandler):
    """SASL authentication handler XMPP streams.

    :Ivariables:
        - `peer_sasl_mechanisms`: SASL mechanisms offered by peer
        - `authenticator`: the authenticator object
    :Types:
        - `peer_sasl_mechanisms`: `list` of `unicode`
        - `authenticator`: `sasl.ClientAuthenticator` or
          `sasl.ServerAuthenticator`
    """
    def __init__(self, settings = None):
        """Initialize the SASL handler"""
        if settings is None:
            settings = XMPPSettings()
        self.settings = settings
        self.peer_sasl_mechanisms = None
        self.authenticator = None

    def make_stream_features(self, stream, features):
        """Add SASL features to the <features/> element of the stream.

        [receving entity only]

        :returns: update <features/> element."""
        mechs = self.settings['sasl_mechanisms']
        if mechs and not stream.authenticated:
            sub = ElementTree.SubElement(features, MECHANISMS_TAG)
            for mech in mechs:
                if mech in sasl.SERVER_MECHANISMS:
                    ElementTree.SubElement(sub, MECHANISM_TAG).text = mech
        return features

    def handle_stream_features(self, stream, features):
        """Process incoming <stream:features/> element.

        [initiating entity only]
        """
        element = features.find(MECHANISMS_TAG)
        self.peer_sasl_mechanisms = []
        if element is None:
            return None
        for sub in element:
            if sub.tag != MECHANISM_TAG:
                continue
            self.peer_sasl_mechanisms.append(sub.text)

        if stream.authenticated or not self.peer_sasl_mechanisms:
            return StreamFeatureNotHandled("SASL", mandatory = True)

        username = self.settings.get("username")
        if not username:
            # TODO: other rules for s2s
            if stream.me.local:
                username = stream.me.local
            else:
                username = None
        self._sasl_authenticate(stream, username, self.settings.get("authzid"))
        return StreamFeatureHandled("SASL", mandatory = True)

    @stream_element_handler(AUTH_TAG, "receiver")
    def process_sasl_auth(self, stream, element):
        """Process incoming <sasl:auth/> element.

        [receiving entity only]
        """
        if self.authenticator:
            logger.debug("Authentication already started")
            return False

        password_db = self.settings["password_database"]
        mechanism = element.get("mechanism")
        if not mechanism:
            stream.send_stream_error("bad-format")
            raise FatalStreamError("<sasl:auth/> with no mechanism")

        stream.auth_method_used = mechanism
        self.authenticator = sasl.server_authenticator_factory(mechanism,
                                                                password_db)

        content = element.text.encode("us-ascii")
        ret = self.authenticator.start(stream.auth_properties,
                                                a2b_base64(content))

        if isinstance(ret, sasl.Success):
            element = ElementTree.Element(SUCCESS_TAG)
            element.text = ret.encode()
        elif isinstance(ret, sasl.Challenge):
            element = ElementTree.Element(CHALLENGE_TAG)
            element.text = ret.encode()
        else:
            element = ElementTree.Element(FAILURE_TAG)
            ElementTree.SubElement(element, SASL_QNP + ret.reason)

        stream.write_element(element)

        if isinstance(ret, sasl.Success):
            self._handle_auth_success(stream, ret)
        elif isinstance(ret, sasl.Failure):
            raise SASLAuthenticationFailed("SASL authentication failed: {0}"
                                                            .format(ret.reason))
        return True

    def _handle_auth_success(self, stream, success):
        """Handle successful authentication.

        Send <success/> and mark the stream peer authenticated.

        [receiver only]
        """
        if not self._check_authorization(success.properties, stream):
            element = ElementTree.Element(FAILURE_TAG)
            ElementTree.SubElement(element, SASL_QNP + "invalid-authzid")
            return True
        authzid = success.properties.get("authzid")
        if authzid:
            peer = JID(success.authzid)
        elif "username" in success.properties:
            peer = JID(success.properties["username"], stream.me.domain)
        else:
            # anonymous
            peer = None
        stream.set_peer_authenticated(peer, True)

    @stream_element_handler(CHALLENGE_TAG, "initiator")
    def _process_sasl_challenge(self, stream, element):
        """Process incoming <sasl:challenge/> element.

        [initiating entity only]
        """
        if not self.authenticator:
            logger.debug("Unexpected SASL challenge")
            return False

        content = element.text.encode("us-ascii")
        ret = self.authenticator.challenge(a2b_base64(content))
        if isinstance(ret, sasl.Response):
            element = ElementTree.Element(RESPONSE_TAG)
            element.text = ret.encode()
        else:
            element = ElementTree.Element(ABORT_TAG)

        stream.write_element(element)

        if isinstance(ret, sasl.Failure):
            stream.disconnect()
            raise SASLAuthenticationFailed("SASL authentication failed")

        return True

    @stream_element_handler(RESPONSE_TAG, "receiver")
    def _process_sasl_response(self, stream, element):
        """Process incoming <sasl:response/> element.

        [receiving entity only]
        """
        if not self.authenticator:
            logger.debug("Unexpected SASL response")
            return False

        content = element.text.encode("us-ascii")
        ret = self.authenticator.response(a2b_base64(content))
        if isinstance(ret, sasl.Success):
            element = ElementTree.Element(SUCCESS_TAG)
            element.text = ret.encode()
        elif isinstance(ret, sasl.Challenge):
            element = ElementTree.Element(CHALLENGE_TAG)
            element.text = ret.encode()
        else:
            element = ElementTree.Element(FAILURE_TAG)
            ElementTree.SubElement(element, SASL_QNP + ret.reason)

        stream.write_element(element)

        if isinstance(ret, sasl.Success):
            self._handle_auth_success(stream, ret)
        elif isinstance(ret, sasl.Failure):
            raise SASLAuthenticationFailed("SASL authentication failed: {0!r}"
                                                            .format(ret.reson))
        return True

    def _check_authorization(self, properties, stream):
        """Check authorization id and other properties returned by the
        authentication mechanism.

        [receiving entity only]

        Allow only no authzid or authzid equal to current username@domain

        FIXME: other rules in s2s

        :Parameters:
            - `properties`: data obtained during authentication
        :Types:
            - `properties`: mapping

        :return: `True` if user is authorized to use a provided authzid
        :returntype: `bool`
        """
        authzid = properties.get("authzid")
        if not authzid:
            return True
        try:
            jid = JID(authzid)
        except ValueError:
            return False

        if "username" not in properties:
            result = False
        elif jid.local != properties["username"]:
            result = False
        elif jid.domain != stream.me.domain:
            result = False
        elif jid.resource:
            result = False
        else:
            result = True
        return result

    @stream_element_handler(SUCCESS_TAG, "initiator")
    def _process_sasl_success(self, stream, element):
        """Process incoming <sasl:success/> element.

        [initiating entity only]

        """
        if not self.authenticator:
            logger.debug("Unexpected SASL response")
            return False

        content = element.text

        if content:
            data = a2b_base64(content.encode("us-ascii"))
        else:
            data = None
        ret = self.authenticator.finish(data)
        if isinstance(ret, sasl.Success):
            logger.debug("SASL authentication succeeded")
            authzid = ret.properties.get("authzid")
            if authzid:
                me = JID(authzid)
            elif "username" in ret.properties:
                # FIXME: other rules for server
                me = JID(ret.properties["username"], stream.peer.domain)
            else:
                me = None
            stream.set_authenticated(me, True)
        else:
            logger.debug("SASL authentication failed")
            raise SASLAuthenticationFailed("Additional success data"
                                                        " procesing failed")
        return True

    @stream_element_handler(FAILURE_TAG, "initiator")
    def _process_sasl_failure(self, stream, element):
        """Process incoming <sasl:failure/> element.

        [initiating entity only]
        """
        _unused = stream
        if not self.authenticator:
            logger.debug("Unexpected SASL response")
            return False

        logger.debug("SASL authentication failed: {0!r}".format(
                                                element_to_unicode(element)))
        raise SASLAuthenticationFailed("SASL authentication failed")

    @stream_element_handler(ABORT_TAG, "receiver")
    def _process_sasl_abort(self, stream, element):
        """Process incoming <sasl:abort/> element.

        [receiving entity only]"""
        _unused, _unused = stream, element
        if not self.authenticator:
            logger.debug("Unexpected SASL response")
            return False

        self.authenticator = None
        logger.debug("SASL authentication aborted")
        return True

    def _sasl_authenticate(self, stream, username, authzid):
        """Start SASL authentication process.

        [initiating entity only]

        :Parameters:
            - `username`: user name.
            - `authzid`: authorization ID.
            - `mechanism`: SASL mechanism to use."""
        if not stream.initiator:
            raise SASLAuthenticationFailed("Only initiating entity start"
                                                        " SASL authentication")
        if stream.features is None or not self.peer_sasl_mechanisms:
            raise SASLNotAvailable("Peer doesn't support SASL")

        props = dict(stream.auth_properties)
        if not props.get("service-domain") and (
                                        stream.peer and stream.peer.domain):
            props["service-domain"] = stream.peer.domain
        if username is not None:
            props["username"] = username
        if authzid is not None:
            props["authzid"] = authzid
        if "password" in self.settings:
            props["password"] = self.settings["password"]
        props["available_mechanisms"] = self.peer_sasl_mechanisms
        enabled = sasl.filter_mechanism_list(
                            self.settings['sasl_mechanisms'], props,
                                            self.settings['insecure_auth'])
        if not enabled:
            raise SASLNotAvailable(
                                "None of SASL mechanism selected can be used")
        props["enabled_mechanisms"] = enabled

        mechanism = None
        for mech in enabled:
            if mech in self.peer_sasl_mechanisms:
                mechanism = mech
                break
        if not mechanism:
            raise SASLMechanismNotAvailable("Peer doesn't support any of"
                                                    " our SASL mechanisms")
        logger.debug("Our mechanism: {0!r}".format(mechanism))

        stream.auth_method_used = mechanism
        self.authenticator = sasl.client_authenticator_factory(mechanism)
        initial_response = self.authenticator.start(props)
        if not isinstance(initial_response, sasl.Response):
            raise SASLAuthenticationFailed("SASL initiation failed")

        element = ElementTree.Element(AUTH_TAG)
        element.set("mechanism", mechanism)
        if initial_response.data:
            if initial_response.encode:
                element.text = initial_response.encode()
            else:
                element.text = initial_response.data
        stream.write_element(element)

XMPPSettings.add_setting(u"username", type = unicode, default = None,
        cmdline_help = u"Username to use instead of the JID local part",
        doc = u"""The username to use instead of the JID local part."""
    )
XMPPSettings.add_setting(u"password", type = unicode, basic = True,
        default = None,
        cmdline_help = u"User password",
        doc = u"""A password for password-based SASL mechanisms."""
    )
XMPPSettings.add_setting(u"authzid", type = unicode, default = None,
        cmdline_help = u"Authorization id for SASL",
        doc = u"""The authorization-id (alternative JID) to request during the
SASL authentication."""
    )
XMPPSettings.add_setting(u"sasl_mechanisms",
        type = 'list of ``unicode``',
        validator = XMPPSettings.validate_string_list,
        default = ["SCRAM-SHA-1-PLUS", "SCRAM-SHA-1", "DIGEST-MD5", "PLAIN"],
        cmdline_help = u"SASL mechanism to enable",
        doc = u"""SASL mechanism that can be used for stream authentication."""
    )
XMPPSettings.add_setting(u"insecure_auth", basic = True,
        type = bool,
        default = False,
        cmdline_help = u"Enable insecure SASL mechanisms over unencrypted channels",
        doc = u"""Enable insecure SASL mechanisms over unencrypted channels"""
    )
XMPPSettings.add_setting(u"password_database",
        type = sasl.PasswordDatabase,
        factory = DefaultPasswordDatabase,
        default_d = "A `DefaultPasswordDatabase` instance",
        doc = u"""Object providing or checking user passwords on server."""
    )


# vi: sts=4 et sw=4
