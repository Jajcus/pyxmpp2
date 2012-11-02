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
"""SASL authentication implementaion for PyXMPP.

Normative reference:
  - `RFC 4422 <http://www.ietf.org/rfc/rfc4422.txt>`__
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import logging

from .core import Reply, Response, Challenge, Success, Failure
from .core import PasswordDatabase
from .core import CLIENT_MECHANISMS, SECURE_CLIENT_MECHANISMS
from .core import SERVER_MECHANISMS, SECURE_SERVER_MECHANISMS
from .core import CLIENT_MECHANISMS_D, SERVER_MECHANISMS_D

from . import plain
from . import external
from . import digest_md5
from . import scram
from . import xfacebookplatform

try:
    from . import gssapi
except ImportError:
    pass # Kerberos not available

logger = logging.getLogger("pyxmpp2.sasl")

def client_authenticator_factory(mechanism):
    """Create a client authenticator object for given SASL mechanism.

    :Parameters:
        - `mechanism`: name of the SASL mechanism ("PLAIN", "DIGEST-MD5" or
          "GSSAPI").
    :Types:
        - `mechanism`: `unicode`

    :raises `KeyError`: if no client authenticator is available for this
              mechanism

    :return: new authenticator.
    :returntype: `sasl.core.ClientAuthenticator`"""
    authenticator = CLIENT_MECHANISMS_D[mechanism]
    return authenticator()

def server_authenticator_factory(mechanism, password_database):
    """Create a server authenticator object for given SASL mechanism and
    password databaser.

    :Parameters:
        - `mechanism`: name of the SASL mechanism ("PLAIN", "DIGEST-MD5" or "GSSAPI").
        - `password_database`: name of the password database object to be used
          for authentication credentials verification.
    :Types:
        - `mechanism`: `str`
        - `password_database`: `PasswordDatabase`

    :raises `KeyError`: if no server authenticator is available for this
              mechanism

    :return: new authenticator.
    :returntype: `sasl.core.ServerAuthenticator`"""
    authenticator = SERVER_MECHANISMS_D[mechanism]
    return authenticator(password_database)

def filter_mechanism_list(mechanisms, properties, allow_insecure = False,
                            server_side = False):
    """Filter a mechanisms list only to include those mechanisms that cans
    succeed with the provided properties and are secure enough.

    :Parameters:
        - `mechanisms`: list of the mechanisms names
        - `properties`: available authentication properties
        - `allow_insecure`: allow insecure mechanisms
    :Types:
        - `mechanisms`: sequence of `unicode`
        - `properties`: mapping
        - `allow_insecure`: `bool`

    :returntype: `list` of `unicode`
    """
    # pylint: disable=W0212
    result = []
    for mechanism in mechanisms:
        try:
            if server_side:
                klass = SERVER_MECHANISMS_D[mechanism]
            else:
                klass = CLIENT_MECHANISMS_D[mechanism]
        except KeyError:
            logger.debug(" skipping {0} - not supported".format(mechanism))
            continue
        secure = properties.get("security-layer")
        if not allow_insecure and not klass._pyxmpp_sasl_secure and not secure:
            logger.debug(" skipping {0}, as it is not secure".format(mechanism))
            continue
        if not klass.are_properties_sufficient(properties):
            logger.debug(" skipping {0}, as the properties are not sufficient"
                                                            .format(mechanism))
            continue
        result.append(mechanism)
    return result
