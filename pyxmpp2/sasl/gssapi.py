#
# (C) Copyright 2008 Jelmer Vernooij <jelmer@samba.org>
# (C) Copyright 2011 Jacek Konieczny <jajcus@jajcus.net>
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
"""GSSAPI authentication mechanism for PyXMPP SASL implementation.

Normative reference:
  - `RFC 4752 <http://www.ietf.org/rfc/rfc4752.txt>`__
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import base64
import kerberos

import logging

from .core import ClientAuthenticator, Response, Success
from .core import sasl_mechanism
        
logger = logging.getLogger("pyxmpp2.sasl.gssapi")

@sasl_mechanism("GSSAPI", 75)
class GSSAPIClientAuthenticator(ClientAuthenticator):
    """Provides client-side GSSAPI SASL (Kerberos 5) authentication."""

    def __init__(self, settings=None):
        ClientAuthenticator.__init__(self, settings)
        self.username = None
        self._gss = None
        self.step = None
        self.authzid = None

    @classmethod
    def are_properties_sufficient(cls, properties):
        return "username" in properties and ("authzid" in properties or
                                            "service-hostname" in properties)

    def start(self, properties):
        self.username = properties["username"]
        self.authzid = properties.get("authzid")
        _unused, self._gss = kerberos.authGSSClientInit(self.authzid or 
                    "{0}@{1}".format("xmpp", properties["service-hostname"]))
        self.step = 0
        return self.challenge(b"")

    def challenge(self, challenge):
        if self.step == 0:
            ret = kerberos.authGSSClientStep(self._gss,
                                                base64.b64encode(challenge))
            if ret != kerberos.AUTH_GSS_CONTINUE:
                self.step = 1
        elif self.step == 1:
            ret = kerberos.authGSSClientUnwrap(self._gss,
                                                base64.b64encode(challenge))
            response = kerberos.authGSSClientResponse(self._gss)
            ret = kerberos.authGSSClientWrap(self._gss, response, self.username)
        response = kerberos.authGSSClientResponse(self._gss)
        if response is None:
            return Response(b"")
        else:
            return Response(base64.b64decode(response))

    def finish(self, data):
        self.username = kerberos.authGSSClientUserName(self._gss)
        logger.debug("Authenticated as {0!r}".format(
                                    kerberos.authGSSClientUserName(self._gss)))
        return Success({"username": self.username, "authzid": self.authzid})

# vi: sts=4 et sw=4
