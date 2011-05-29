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

"""Generic XMPP stream implementation.

Normative reference:
  - `RFC 6120 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import logging

from .streambase import StreamBase
from .streamtls import StreamTLSMixIn
from .streamsasl import StreamSASLMixIn

class Stream(StreamTLSMixIn, StreamSASLMixIn, StreamBase):
    """Generic XMPP stream class.

    Responsible for establishing connection, parsing the stream,
    StartTLS encryption and SASL authentication negotiation
    and usage, dispatching received stanzas to apopriate handlers
    and sending application's stanzas.

    Whenever we say "stream" here we actually mean two streams
    (incoming and outgoing) of one connections, as defined by the XMPP
    specification.
    """
    # pylint: disable-msg=R0904
    def __init__(self, stanza_namespace, event_handler, settings = None):
        """Initialize Stream object

        :Parameters:
          - `stanza_namespace`: stream's default namespace URI ("jabber:client"
            for client, "jabber:server" for server, etc.)
          - `event_handler`: object to handle the stream events
          - `settings`: extra settings
        :Types:
          - `stanza_namespace`: `unicode`
          - `settings`: XMPPSettings
          - `event_handler`: `XMPPEventHandler`
        """
        StreamBase.__init__(self, stanza_namespace, event_handler, settings)
        StreamTLSMixIn.__init__(self)
        StreamSASLMixIn.__init__(self)
        self.__logger = logging.getLogger("pyxmpp.Stream")

    def _make_stream_features(self):
        """Create the <features/> element for the stream.

        [receving entity only]

        :returns: new <features/> element node."""
        features = StreamBase._make_stream_features(self)
        self._make_stream_tls_features(features)
        self._make_stream_sasl_features(features)
        return features

    def _process_element(self, element):
        """Process first level element of the stream.

        The element may be stream error or features, StartTLS
        request/response, SASL request/response or a stanza.

        :Parameters:
            - `element`: XML element
        :Types:
            - `element`: `ElementTree.Element`
        """
        if self._process_element_tls(element):
            return
        if self._process_element_sasl(element):
            return
        StreamBase._process_element(self, element)

    def _got_features(self):
        """Process incoming <stream:features/> element.

        [initiating entity only]

        The received features node is available in `self.features`."""
        self._handle_tls_features()
        self._handle_sasl_features()
        StreamBase._got_features(self)

    def event(self, event):
        """Handle a stream event.
        
        Called when connection state is changed.

        Must not be called with self.lock acquired!
        """
        handled = StreamBase.event(self, event)
        if not handled:
            handled = StreamSASLMixIn.event(self, event)
        if not handled:
            handled = StreamTLSMixIn.event(self, event)
        return handled 

# vi: sts=4 et sw=4
