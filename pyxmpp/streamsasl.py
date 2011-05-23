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

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import base64
import logging
from xml.etree import ElementTree

from .jid import JID
from . import sasl
from .exceptions import SASLNotAvailable
from .exceptions import SASLMechanismNotAvailable, SASLAuthenticationFailed
from .constants import SASL_QNP
from .settings import XMPPSettings
from .streamevents import AuthenticatedEvent
        
logger = logging.getLogger("pyxmpp.streamsasl")

class DefaultPasswordManager(sasl.PasswordManager):
    """Default password manager."""
    def __init__(self, settings):
        self.settings = settings
        sasl.PasswordManager.__init__(self)

XMPPSettings.add_default_factory("password_manager", DefaultPasswordManager)

MECHANISMS_TAG = SASL_QNP + u"mechanisms"
MECHANISM_TAG = SASL_QNP + u"mechanism"
CHALLENGE_TAG = SASL_QNP + u"challenge"
SUCCESS_TAG = SASL_QNP + u"success"
FAILURE_TAG = SASL_QNP + u"failure"
AUTH_TAG = SASL_QNP + u"auth"
RESPONSE_TAG = SASL_QNP + u"response"
ABORT_TAG = SASL_QNP + u"abort"

class StreamSASLMixIn(object):
    """SASL authentication mix-in class for XMPP stream.

    :Ivariables:
        `peer_sasl_mechanisms`: SASL mechanisms offered by peer
        `authenticator`: the authenticator object
    :Types:
        `peer_sasl_mechanisms`: `list` of `unicode`
        `authenticator`: `sasl.ClientAuthenticator` or `sasl.ServerAuthenticator`
    """
    # pylint: disable-msg=R0903,R0902
    def __init__(self):
        """Initialize the SASL mix-in"""
        self.password_manager = self.settings["password_manager"]

    def _reset_sasl(self):
        """Reset `StreamSASLMixIn` object state making it ready to handle new
        connections."""
        self.peer_sasl_mechanisms = None
        self.authenticator = None

    def _make_stream_sasl_features(self, features):
        """Add SASL features to the <features/> element of the stream.

        [receving entity only]

        :returns: update <features/> element node."""
        mechs = self.settings['sasl_mechanisms'] 
        if mechs and not self.authenticated:
            sub = ElementTree.SubElement(features, MECHANISMS_TAG)
            for mech in mechs:
                if mech in sasl.all_mechanisms:
                    ElementTree.SubElement(sub, MECHANISM_TAG).text = mech
        return features

    def _handle_sasl_features(self):
        """Process incoming <stream:features/> element.

        [initiating entity only]

        The received features node is available in `self.features`."""
        element = self.features.find(MECHANISMS_TAG)
        self.peer_sasl_mechanisms = []
        if not element:
            return
        for sub in element:
            if sub.tag != MECHANISM_TAG:
                continue
            self.peer_sasl_mechanisms.append(sub.text)

    def _process_element_sasl(self, element):
        """Process incoming stream element. Pass it to _process_sasl_element
        if it is in the SASL namespace.

        :return: `True` when the element was recognized as a SASL element.
        :returntype: `bool`
        """
        if element.tag.startswith(SASL_QNP):
            self._process_sasl_element(element)
            return True
        return False

    def _process_sasl_element(self, element):
        """Process stream element in the SASL namespace.

        :Parameters:
            - `element`: the XML element
        """
        if self.initiator:
            if not self.authenticator:
                logger.debug("Unexpected SASL response: {0!r}".format(
                                                ElementTree.tostring(element)))
                ret = False
            elif element.tag == CHALLENGE_TAG:
                ret = self._process_sasl_challenge(element.text)
            elif element.tag == SUCCESS_TAG:
                ret = self._process_sasl_success(element.text)
            elif element.tag == FAILURE_TAG:
                ret = self._process_sasl_failure(element)
            else:
                logger.debug("Unexpected SASL element: {0!r}".format(
                                                ElementTree.tostring(element)))
                ret = False
        else:
            if element.tag == AUTH_TAG:
                mechanism = element.get("mechanism")
                ret = self._process_sasl_auth(mechanism, element.text)
            if element.tag == RESPONSE_TAG:
                ret = self._process_sasl_response(element.text)
            if element.tag == ABORT_TAG:
                ret = self._process_sasl_abort()
            else:
                logger.debug("Unexpected SASL element: {0!r}".format(
                                                ElementTree.tostring(element)))
                ret = False
        return ret

    def _process_sasl_auth(self, mechanism, content):
        """Process incoming <sasl:auth/> element.

        [receiving entity only]

        :Parameters:
            - `mechanism`: mechanism choosen by the peer.
            - `content`: optional "initial response" included in the element.
        """
        if self.authenticator:
            logger.debug("Authentication already started")
            return False

        self.auth_method_used = mechanism
        self.authenticator = sasl.server_authenticator_factory(mechanism, 
                                                        self.password_manager)
        ret = self.authenticator.start(base64.decodestring(content))

        if isinstance(ret, sasl.Success):
            element = ElementTree.Element(SUCCESS_TAG)
            element.text = ret.base64()
        elif isinstance(ret, sasl.Challenge):
            element = ElementTree.Element(CHALLENGE_TAG)
            element.text = ret.base64()
        else:
            element = ElementTree.Element(FAILURE_TAG)
            ElementTree.SubElement(element, SASL_QNP + ret.reason)

        self._write_element(element)

        if isinstance(ret, sasl.Success):
            if ret.authzid:
                self.peer = JID(ret.authzid)
            else:
                self.peer = JID(ret.username, self.me.domain)
            self.peer_authenticated = True
            self.event(AuthenticatedEvent(self.peer))
        elif isinstance(ret, sasl.Failure):
            raise SASLAuthenticationFailed("SASL authentication failed: {0}"
                                                            .format(ret.reason))
        
        return True

    def _process_sasl_challenge(self, content):
        """Process incoming <sasl:challenge/> element.

        [initiating entity only]

        :Parameters:
            - `content`: the challenge data received (Base64-encoded).
        """
        if not self.authenticator:
            logger.debug("Unexpected SASL challenge")
            return False

        ret = self.authenticator.challenge(base64.decodestring(content))
        if isinstance(ret, sasl.Response):
            element = ElementTree.Element(RESPONSE_TAG)
            element.text = ret.base64()
        else:
            element = ElementTree.Element(ABORT_TAG)

        self._write_element(element)

        if isinstance(ret, sasl.Failure):
            raise SASLAuthenticationFailed("SASL authentication failed")

        return True

    def _process_sasl_response(self, content):
        """Process incoming <sasl:response/> element.

        [receiving entity only]

        :Parameters:
            - `content`: the response data received (Base64-encoded).
        """
        if not self.authenticator:
            logger.debug("Unexpected SASL response")
            return 0

        ret = self.authenticator.response(base64.decodestring(content))
        if isinstance(ret, sasl.Success):
            element = ElementTree.Element(SUCCESS_TAG)
            element.text = ret.base64()
        elif isinstance(ret, sasl.Challenge):
            element = ElementTree.Element(CHALLENGE_TAG)
            element.text = ret.base64()
        else:
            element = ElementTree.Element(FAILURE_TAG)
            ElementTree.SubElement(element, SASL_QNP + ret.reason)

        self._write_element(element)

        if isinstance(ret, sasl.Success):
            authzid = ret.authzid
            if authzid:
                self.peer = JID(ret.authzid)
            else:
                self.peer = JID(ret.username, self.me.domain)
            self.peer_authenticated = True
            self._restart_stream()
            self.event(AuthenticatedEvent(self.peer))

        if isinstance(ret, sasl.Failure):
            raise SASLAuthenticationFailed("SASL authentication failed: {0!r}"
                                                            .format(ret.reson))

        return True

    def _process_sasl_success(self, content):
        """Process incoming <sasl:success/> element.

        [initiating entity only]

        :Parameters:
            - `content`: the "additional data with success" received (Base64-encoded).
        """
        if not self.authenticator:
            logger.debug("Unexpected SASL response")
            return False

        ret = self.authenticator.finish(base64.decodestring(content))
        if isinstance(ret, sasl.Success):
            logger.debug("SASL authentication succeeded")
            if ret.authzid:
                self.me = JID(ret.authzid)
            self.authenticated = True
            self._restart_stream()
            self.event(AuthenticatedEvent(self.me))
        else:
            logger.debug("SASL authentication failed")
            raise SASLAuthenticationFailed("Additional success data"
                                                        " procesing failed")
        return True

    def _process_sasl_failure(self, element):
        """Process incoming <sasl:failure/> element.

        [initiating entity only]

        :Parameters:
            - `element`: the XML element received.
        """
        if not self.authenticator:
            logger.debug("Unexpected SASL response")
            return False

        logger.debug("SASL authentication failed: {0!r}".format(
                                                ElementTree.tostring(element)))
        raise SASLAuthenticationFailed("SASL authentication failed")

    def _process_sasl_abort(self):
        """Process incoming <sasl:abort/> element.

        [receiving entity only]"""
        if not self.authenticator:
            logger.debug("Unexpected SASL response")
            return False

        self.authenticator = None
        logger.debug("SASL authentication aborted")
        return True

    def _sasl_authenticate(self, username, authzid, mechanism = None):
        """Start SASL authentication process.

        [initiating entity only]

        :Parameters:
            - `username`: user name.
            - `authzid`: authorization ID.
            - `mechanism`: SASL mechanism to use."""
        if not self.initiator:
            raise SASLAuthenticationFailed("Only initiating entity start"
                                                        " SASL authentication")
        if not self.features or not self.peer_sasl_mechanisms:
            raise SASLNotAvailable("Peer doesn't support SASL")

        mechs = self.settings['sasl_mechanisms'] 
        if not mechanism:
            mechanism = None
            for mech in mechs:
                if mech in self.peer_sasl_mechanisms:
                    mechanism = mech
                    break
            if not mechanism:
                raise SASLMechanismNotAvailable("Peer doesn't support any of"
                                                        " our SASL mechanisms")
            logger.debug("Our mechanism: {0!r}".format(mechanism))
        else:
            if mechanism not in self.peer_sasl_mechanisms:
                raise SASLMechanismNotAvailable("{0!r} is not available"
                                                            .format(mechanism))

        self.auth_method_used = mechanism
        self.authenticator = sasl.client_authenticator_factory(mechanism, self)

        initial_response = self.authenticator.start(username, authzid)
        if not isinstance(initial_response, sasl.Response):
            raise SASLAuthenticationFailed("SASL initiation failed")

        element = ElementTree.Element(AUTH_TAG)
        element.set("mechanism", mechanism)
        if initial_response.data:
            if initial_response.encode:
                element.text = initial_response.base64()
            else:
                element.text = initial_response.data

        self._write_element(element)

# vi: sts=4 et sw=4
