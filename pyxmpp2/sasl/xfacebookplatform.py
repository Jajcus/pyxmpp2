#
# (C) Copyright 2012 Ramnath Krishnamurthy <k.ramnath@gmail.com>
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
"""XFacebookPlatform authentication mechanism for PyXMPP SASL implementation.

Normative reference:
  - `RFC 4752 <http://www.ietf.org/rfc/rfc4752.txt>`__
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import logging

from .core import ClientAuthenticator, Response, Success
from .core import sasl_mechanism

import time, urllib

logger = logging.getLogger("pyxmpp2.sasl.xfb")

@sasl_mechanism(name='X-FACEBOOK-PLATFORM', secure=False, preference=100)
class XFacebookPlatformClientAuthenticator(ClientAuthenticator):
    """Provides client-side XFacebookPlatform authentication."""
    def __init__(self):
        self.access_token = None
        self.api_key = None
        ClientAuthenticator.__init__(self)

    @classmethod
    def are_properties_sufficient(cls, properties):
        if ('facebook_access_token' in properties
                            and 'facebook_api_key' in properties):
            return True
        return False

    def start(self, properties):
        self.access_token = properties['facebook_access_token']
        self.api_key = properties['facebook_api_key']
        return Response(None)

    def challenge(self, challenge):
        in_params = dict([part.split('=') for part in challenge.split('&')])
        out_params = {}
        out_params['nonce'] = in_params['nonce']
        out_params['method'] = in_params['method']
        out_params['access_token'] = self.access_token
        out_params['api_key'] = self.api_key
        out_params['call_id'] = float(round(time.time() * 1000))
        out_params['v'] = '1.0'
        data = urllib.urlencode(out_params)
        return Response(data)

    def finish(self, data):
        return Success(None)

