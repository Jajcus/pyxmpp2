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
"""PLAIN authentication mechanism for PyXMPP SASL implementation.

Normative reference:
  - `RFC 4616 <http://www.ietf.org/rfc/rfc4616.txt>`__
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import logging

from .core import ClientAuthenticator, ServerAuthenticator
from .core import Success, Failure, Challenge, Response
from .core import sasl_mechanism

logger = logging.getLogger("pyxmpp2.sasl.plain")

@sasl_mechanism("PLAIN", 10)
class PlainClientAuthenticator(ClientAuthenticator):
    """Provides PLAIN SASL authentication for a client.

    Authentication properties used:

        - ``"username"`` - user name (required)
        - ``"authzid"`` - authorization id (optional)

    Authentication properties returned:

        - ``"username"`` - user name
        - ``"authzid"`` - authorization id
    """
    def __init__(self):
        ClientAuthenticator.__init__(self)
        self.username = None
        self.finished = None
        self.password = None
        self.authzid = None
        self.properties = None

    @classmethod
    def are_properties_sufficient(cls, properties):
        return "username" in properties and "password" in properties

    def start(self, properties):
        self.properties = properties
        self.username = properties["username"]
        self.authzid = properties.get("authzid", u"")
        self.finished = False
        return self.challenge(b"")

    def challenge(self, challenge):
        if self.finished:
            logger.debug(u"Already authenticated")
            return Failure(u"extra-challenge")
        self.finished = True
        password = self.properties["password"]
        return Response(b"\000".join(( self.authzid.encode("utf-8"),
                            self.username.encode("utf-8"),
                            password.encode("utf-8"))))

    def finish(self, data):
        return Success({"username": self.username, "authzid": self.authzid})

@sasl_mechanism("PLAIN", 10)
class PlainServerAuthenticator(ServerAuthenticator):
    """Provides PLAIN SASL authentication for a server.

    Authentication properties used: None

    Authentication properties returned:

        - ``"username"`` - user name
        - ``"authzid"`` - authorization id
    """
    def __init__(self, password_database):
        ServerAuthenticator.__init__(self, password_database)
        self.properties = None

    def start(self, properties, initial_response):
        self.properties = properties
        if not initial_response:
            return Challenge(b"")
        return self.response(initial_response)

    def response(self, response):
        fields = response.split(b"\000")
        if len(fields) != 3:
            logger.debug(u"Bad response: {0!r}".format(response))
            return Failure("not-authorized")
        authzid, username, password = fields
        authzid = authzid.decode("utf8")
        username = username.decode("utf8")
        password = password.decode("utf8")
        out_props = {"username": username, "authzid": authzid}
        props = dict(self.properties)
        props.update(out_props)
        if not self.password_database.check_password(username, password,
                                                            self.properties):
            logger.debug("Bad password. Response was: {0!r}".format(response))
            return Failure("not-authorized")
        return Success(out_props)

# vi: sts=4 et sw=4
