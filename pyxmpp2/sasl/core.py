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
"""Base classes for PyXMPP SASL implementation.

Normative reference:
  - `RFC 4422 <http://www.ietf.org/rfc/rfc4422.txt>`__


Authentication properties
-------------------------

Most authentication mechanisms needs some data to identify the
authenticating entity and/or to provide characteristics of the communication
channel. These are passed as a `properties` mapping to the ``.start()``
method to a server or client authenticator.

Similar mechanism is used to return data obtained via the authentication
process: the `Success` object has a `Success.properties` attribute with
the data obtained.

The mapping contains name->value pairs. Meaning of those is generally
mechanism-dependant, but these are the usually expected properties:

  * For input to the ``start()`` method:

    * ``"username"`` - the user name. Required by all password based mechanisms.
    * ``"password"`` - the user's password.  Required by all password based
      mechanisms.
    * ``"authzid"`` - authorization id. Optional for most mechanisms.
    * ``"security-layer"`` - security layer if any. ``"TLS"`` when TLS is in
      use.
    * ``"channel-binding"`` - mapping of 'channel binding type' to 'channel
      binding date' if available on the channel
    * ``"service-type"`` - service type as required by the DIGEST-MD5 protocol
    * ``"service-domain"`` - service domain (the 'serv-name' or 'host' part of
      diges-uri of DIGEST-MD5)
    * ``"service-hostname"`` - service host name (the 'host' par of diges-uri
      of DIGEST-MD5)
    * ``"remote-ip"`` - remote IP address
    * ``"realm"`` - the realm to use if needed
    * ``"realms"`` - list of acceptable realms
    * ``"available_mechanisms"`` - mechanism list provided by peer
    * ``"enabled_mechanisms"`` - mechanisms enabled on our side

  * For output, via the `Success.properties` attribute:

    * ``"username"`` - the authenticated user name
    * ``"authzid"`` - the authorization id
    * ``"realm"`` - the realm

"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import uuid
import hashlib
import logging

from base64 import standard_b64encode

from abc import ABCMeta, abstractmethod

try:
    # pylint: disable=E0611
    from abc import abstractclassmethod
except ImportError:
    # pylint: disable=C0103
    abstractclassmethod = classmethod

logger = logging.getLogger("pyxmpp2.sasl.core")

CLIENT_MECHANISMS_D = {}
CLIENT_MECHANISMS = []
SECURE_CLIENT_MECHANISMS = []

SERVER_MECHANISMS_D = {}
SERVER_MECHANISMS = []
SECURE_SERVER_MECHANISMS = []

class PasswordDatabase:
    """Password database interface.

    PasswordDatabase object is responsible for providing or verification of
    user authentication credentials on a server.

    All the methods of the `PasswordDatabase` may be overridden in derived
    classes for specific authentication and authorization policy.
    """
    # pylint: disable-msg=W0232,R0201
    __metaclass__ = ABCMeta
    def get_password(self, username, acceptable_formats, properties):
        """Get the password for user authentication.

        By default returns (None, None) providing no password. Should be
        overridden in derived classes unless only `check_password` functionality
        is available.

        :Parameters:
            - `username`: the username for which the password is requested.
            - `acceptable_formats`: a sequence of acceptable formats of the
              password data. Could be "plain" (plain text password),
              "md5:user:realm:password" (MD5 hex digest of user:realm:password)
              or any other mechanism-specific encoding. This allows
              non-plain-text storage of passwords. But only "plain" format will
              work with all password authentication mechanisms.
            - `properties`: mapping with authentication properties (those
              provided to the authenticator's ``start()`` method plus some
              already obtained via the mechanism).
        :Types:
            - `username`: `unicode`
            - `acceptable_formats`: sequence of `unicode`
            - `properties`: mapping

        :return: the password and its encoding (format).
        :returntype: `unicode`,`unicode` tuple.
        """
        # pylint: disable-msg=W0613
        return None, None

    def check_password(self, username, password, properties):
        """Check the password validity.

        Used by plain-text authentication mechanisms.

        Default implementation: retrieve a "plain" password for the `username`
        and `realm` using `self.get_password` and compare it with the password
        provided.

        May be overridden e.g. to check the password against some external
        authentication mechanism (PAM, LDAP, etc.).

        :Parameters:
            - `username`: the username for which the password verification is
              requested.
            - `password`: the password to verify.
            - `properties`: mapping with authentication properties (those
              provided to the authenticator's ``start()`` method plus some
              already obtained via the mechanism).
        :Types:
            - `username`: `unicode`
            - `password`: `unicode`
            - `properties`: mapping

        :return: `True` if the password is valid.
        :returntype: `bool`
        """
        logger.debug("check_password{0!r}".format(
                                            (username, password, properties)))
        pwd, pwd_format = self.get_password(username,
                    (u"plain", u"md5:user:realm:password"), properties)
        if pwd_format == u"plain":
            logger.debug("got plain password: {0!r}".format(pwd))
            return pwd is not None and password == pwd
        elif pwd_format in (u"md5:user:realm:password"):
            logger.debug("got md5:user:realm:password password: {0!r}"
                                                            .format(pwd))
            realm = properties.get("realm")
            if realm is None:
                realm = ""
            else:
                realm = realm.encode("utf-8")
            username = username.encode("utf-8")
            password = password.encode("utf-8")

            # pylint: disable-msg=E1101
            urp_hash = hashlib.md5(b"%s:%s:%s").hexdigest()
            return urp_hash == pwd
        logger.debug("got password in unknown format: {0!r}".format(pwd_format))
        return False


def default_nonce_factory():
    """Generate a random string for digest authentication challenges.

    The string should be cryptographicaly secure random pattern.

    :return: the string generated.
    :returntype: `bytes`
    """
    return uuid.uuid4().hex.encode("us-ascii")

class Reply(object):
    """Base class for SASL authentication reply objects.

    :Ivariables:
        - `data`: optional reply data.
    :Types:
        - `data`: `bytes`
    """
    # pylint: disable-msg=R0903
    def __init__(self, data = None):
        """Initialize the `Reply` object.

        :Parameters:
            - `data`: optional reply data.
        :Types:
            - `data`: `bytes`
        """
        self.data = data

    def encode(self):
        """Base64-encode the data contained in the reply when appropriate.

        :return: encoded data.
        :returntype: `unicode`
        """
        if self.data is None:
            return ""
        elif not self.data:
            return "="
        else:
            ret = standard_b64encode(self.data)
            return ret.decode("us-ascii")

class Challenge(Reply):
    """The challenge SASL message (server's challenge for the client)."""
    # pylint: disable-msg=R0903
    def __init__(self, data):
        """Initialize the `Challenge` object."""
        Reply.__init__(self, data)
    def __repr__(self):
        return "<sasl.Challenge: {0!r}>".format(self.data)

class Response(Reply):
    """The response SASL message (clients's reply the server's
    challenge)."""
    # pylint: disable-msg=R0903
    def __init__(self, data):
        """Initialize the `Response` object."""
        Reply.__init__(self, data)
    def __repr__(self):
        return "<sasl.Response: {0!r}>".format(self.data)

class Failure(Reply):
    """The failure SASL message.

    :Ivariables:
        - `reason`: the failure reason.
    :Types:
        - `reason`: `unicode`.
    """
    # pylint: disable-msg=R0903
    def __init__(self, reason):
        """Initialize the `Failure` object.

        :Parameters:
            - `reason`: the failure reason.
        :Types:
            - `reason`: `unicode`.
        """
        Reply.__init__(self, None)
        self.reason = reason
    def __repr__(self):
        return "<sasl.Failure: {0!r}>".format(self.reason)

class Success(Reply):
    """The success SASL message (sent by the server on authentication
    success).
    """
    # pylint: disable-msg=R0903
    def __init__(self, properties = None, data = None):
        """Initialize the `Success` object.

        :Parameters:
            - `properties`: the `authentication properties`_ obtained
            - `data`: the success data to be sent to the client
        :Types:
            - `properties`: mapping
            - `data`: `bytes`
        """
        # pylint: disable-msg=R0913
        Reply.__init__(self, data)
        if properties:
            self.properties = properties
        else:
            self.properties = {}

    def __repr__(self):
        return "<sasl.Success: {0!r} data: {1!r}>".format(
                                                    self.properties, self.data)

class ClientAuthenticator:
    """Base class for client authenticators.

    A client authenticator class is a client-side implementation of a SASL
    mechanism. One `ClientAuthenticator` object may be used for one
    client authentication process.
    """
    __metaclass__ = ABCMeta
    def __init__(self):
        """Initialize a `ClientAuthenticator` object."""
        pass

    @abstractclassmethod
    def are_properties_sufficient(cls, properties):
        """Check if the provided properties are sufficient for
        this authentication mechanism.

        If `are_properties_sufficient` returns False for given `properties`
        mapping, the `start` method of `cls` instance will also fail with
        such argument.

        :Parameters:
            - `properties`: the `authentication properties`_
        :Types:
            - `properties`: mapping

        :Return: if the mechanism can be used with those properties
        """
        # pylint: disable=E0213,W0613,R0201
        return False

    @abstractmethod
    def start(self, properties):
        """Start the authentication process.

        :Parameters:
            - `properties`: the `authentication properties`_
        :Types:
            - `properties`: mapping

        :return: the initial response to send to the server or a failuer
            indicator.
        :returntype: `Response` or `Failure`
        """
        raise NotImplementedError

    @abstractmethod
    def challenge(self, challenge):
        """Process the server's challenge.

        :Parameters:
            - `challenge`: the challenge.
        :Types:
            - `challenge`: `bytes`

        :return: the response or a failure indicator.
        :returntype: `Response` or `Failure`"""
        raise NotImplementedError

    @abstractmethod
    def finish(self, data):
        """Handle authentication succes information from the server.

        :Parameters:
            - `data`: the optional additional data returned with the success.
        :Types:
            - `data`: `bytes`

        :return: success or failure indicator.
        :returntype: `Success` or `Failure`"""
        raise NotImplementedError

class ServerAuthenticator:
    """Base class for server authenticators.

    A server authenticator class is a server-side implementation of a SASL
    mechanism. One `ServerAuthenticator` object may be used for one
    client authentication process.
    """
    __metaclass__ = ABCMeta
    def __init__(self, password_database):
        """Initialize a `ServerAuthenticator` object.

        :Parameters:
            - `password_database`: a password database
        :Types:
            - `password_database`: `PasswordDataBase`
        """
        self.password_database = password_database

    @classmethod
    def are_properties_sufficient(cls, properties):
        """Check if the provided properties are sufficient for
        this authentication mechanism.

        If `are_properties_sufficient` returns False for given `properties`
        mapping, the `start` method of `cls` instance will also fail with
        such argument.

        :Parameters:
            - `properties`: the `authentication properties`_
        :Types:
            - `properties`: mapping

        :Return: if the mechanism can be used with those properties
        """
        # pylint: disable=E0213,W0613,R0201
        return True

    @abstractmethod
    def start(self, properties, initial_response):
        """Start the authentication process.

        :Parameters:
            - `properties`: the `authentication properties`_
            - `initial_response`: the initial response send by the client with
              the authentication request.

        :Types:
            - `properties`: mapping
            - `initial_response`: `bytes`

        :return: a challenge, a success or a failure indicator.
        :returntype: `Challenge` or `Failure` or `Success`"""
        raise NotImplementedError

    @abstractmethod
    def response(self, response):
        """Process a response from a client.

        :Parameters:
            - `response`: the response from the client to our challenge.
        :Types:
            - `response`: `bytes`

        :return: a challenge, a success or a failure indicator.
        :returntype: `Challenge` or `Success` or `Failure`"""
        raise NotImplementedError

def _key_func(item):
    """Key function used for sorting SASL authenticator classes
    """
    # pylint: disable-msg=W0212
    klass = item[1]
    return (klass._pyxmpp_sasl_secure, klass._pyxmpp_sasl_preference)

def _register_client_authenticator(klass, name):
    """Add a client authenticator class to `CLIENT_MECHANISMS_D`,
    `CLIENT_MECHANISMS` and, optionally, to `SECURE_CLIENT_MECHANISMS`
    """
    # pylint: disable-msg=W0212
    CLIENT_MECHANISMS_D[name] = klass
    items = sorted(CLIENT_MECHANISMS_D.items(), key = _key_func, reverse = True)
    CLIENT_MECHANISMS[:] = [k for (k, v) in items ]
    SECURE_CLIENT_MECHANISMS[:] = [k for (k, v) in items
                                                    if v._pyxmpp_sasl_secure]

def _register_server_authenticator(klass, name):
    """Add a client authenticator class to `SERVER_MECHANISMS_D`,
    `SERVER_MECHANISMS` and, optionally, to `SECURE_SERVER_MECHANISMS`
    """
    # pylint: disable-msg=W0212
    SERVER_MECHANISMS_D[name] = klass
    items = sorted(SERVER_MECHANISMS_D.items(), key = _key_func, reverse = True)
    SERVER_MECHANISMS[:] = [k for (k, v) in items ]
    SECURE_SERVER_MECHANISMS[:] = [k for (k, v) in items
                                                    if v._pyxmpp_sasl_secure]

def sasl_mechanism(name, secure, preference = 50):
    """Class decorator generator for `ClientAuthenticator` or
    `ServerAuthenticator` subclasses. Adds the class to the pyxmpp.sasl
    mechanism registry.

    :Parameters:
        - `name`: SASL mechanism name
        - `secure`: if the mechanims can be considered secure - `True`
          if it can be used over plain-text channel
        - `preference`: mechanism preference level (the higher the better)
    :Types:
        - `name`: `unicode`
        - `secure`: `bool`
        - `preference`: `int`
    """
    # pylint: disable-msg=W0212
    def decorator(klass):
        """The decorator."""
        klass._pyxmpp_sasl_secure = secure
        klass._pyxmpp_sasl_preference = preference
        if issubclass(klass, ClientAuthenticator):
            _register_client_authenticator(klass, name)
        elif issubclass(klass, ServerAuthenticator):
            _register_server_authenticator(klass, name)
        else:
            raise TypeError("Not a ClientAuthenticator"
                                            " or ServerAuthenticator class")
        return klass
    return decorator

# vi: sts=4 et sw=4
