#
# (C) Copyright 2003 Jacek Konieczny <jajcus@bnet.pl>
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

"""Core XMPP stream functionality"""

__revision__="$Id: streamsasl.py,v 1.2 2004/09/28 21:31:00 jajcus Exp $"
__docformat__="restructuredtext en"

import base64
import logging

from pyxmpp.jid import JID
from pyxmpp import sasl
from pyxmpp.streambase import StreamAuthenticationError

SASL_NS="urn:ietf:params:xml:ns:xmpp-sasl"

class SASLNotAvailable(StreamAuthenticationError):
    """Raised when SASL authentication is requested, but not available."""
    pass

class SASLMechanismNotAvailable(StreamAuthenticationError):
    """Raised when none of SASL authentication mechanisms requested is
    available."""
    pass

class SASLAuthenticationFailed(StreamAuthenticationError):
    """Raised when stream SASL authentication fails."""
    pass

class StreamSASLMixIn(sasl.PasswordManager):
    """SASL authentication mix-in class for XMPP stream."""
    def __init__(self,sasl_mechanisms=()):
        """Initialize Stream object

        :Parameters:
          - `sasl_mechanisms`: sequence of SASL mechanisms allowed for
            authentication. Currently "PLAIN" and "DIGEST-MD5" are supported.
        """
        if sasl_mechanisms:
            self.sasl_mechanisms=sasl_mechanisms
        else:
            self.sasl_mechanisms=[]
        self.__logger=logging.getLogger("pyxmpp.StreamSASLMixIn")

    def _reset_sasl(self):
        """Reset `StreamSASLMixIn` object state making it ready to handle new
        connections."""
        self.peer_sasl_mechanisms=None
        self.authenticator=None

    def _make_stream_sasl_features(self,features):
        """Add SASL features to the <features/> element of the stream.

        [receving entity only]
        
        :returns: update <features/> element node."""
        if self.sasl_mechanisms and not self.authenticated:
            ml=features.newChild(None,"mechanisms",None)
            ns=ml.newNs(SASL_NS,None)
            ml.setNs(ns)
            for m in self.sasl_mechanisms:
                if m in sasl.all_mechanisms:
                    ml.newTextChild(ns,"mechanism",m)
        return features

    def _handle_sasl_features(self):
        """Process incoming <stream:features/> element.

        [initiating entity only]

        The received features node is available in `self.features`."""
        ctxt = self.doc_in.xpathNewContext()
        ctxt.setContextNode(self.features)
        ctxt.xpathRegisterNs("sasl",SASL_NS)
        try:
            sasl_mechanisms_n=ctxt.xpathEval("sasl:mechanisms/sasl:mechanism")
        finally:
            ctxt.xpathFreeContext()

        if sasl_mechanisms_n:
            self.__logger.debug("SASL support found")
            self.peer_sasl_mechanisms=[]
            for n in sasl_mechanisms_n:
                self.peer_sasl_mechanisms.append(n.getContent())

    def _process_node_sasl(self,node):
        """Process incoming stream element. Pass it to _process_sasl_node
        if it is in the SASL namespace. 

        :return: `True` when the node was recognized as a SASL element.
        :returntype: `bool`"""
        ns_uri=node.ns().getContent()
        if ns_uri==SASL_NS:
            self._process_sasl_node(node)
            return True
        return False

    def _process_sasl_node(self,node):
        """Process stream element in the SASL namespace.
        
        :Parameters:
            - `node`: the XML node received
        """
        if self.initiator:
            if not self.authenticator:
                self.__logger.debug("Unexpected SASL response: %r" % (node.serialize()))
                ret=False
            elif node.name=="challenge":
                ret=self._process_sasl_challenge(node.getContent())
            elif node.name=="success":
                ret=self._process_sasl_success(node.getContent())
            elif node.name=="failure":
                ret=self._process_sasl_failure(node)
            else:
                self.__logger.debug("Unexpected SASL node: %r" % (node.serialize()))
                ret=False
        else:
            if node.name=="auth":
                mechanism=node.prop("mechanism")
                ret=self._process_sasl_auth(mechanism,node.getContent())
            if node.name=="response":
                ret=self._process_sasl_response(node.getContent())
            if node.name=="abort":
                ret=self._process_sasl_abort()
            else:
                self.__logger.debug("Unexpected SASL node: %r" % (node.serialize()))
                ret=False
        return ret

    def _process_sasl_auth(self,mechanism,content):
        """Process incoming <sasl:auth/> element.

        [receiving entity only]

        :Parameters:
            - `mechanism`: mechanism choosen by the peer.
            - `content`: optional "initial response" included in the element.
        """
        if self.authenticator:
            self.__logger.debug("Authentication already started")
            return False

        self.auth_method_used="sasl:"+mechanism
        self.authenticator=sasl.server_authenticator_factory(mechanism,self)

        r=self.authenticator.start(base64.decodestring(content))

        if isinstance(r,sasl.Success):
            el_name="success"
            content=r.base64()
        elif isinstance(r,sasl.Challenge):
            el_name="challenge"
            content=r.base64()
        else:
            el_name="failure"
            content=None

        root=self.doc_out.getRootElement()
        node=root.newChild(None,el_name,None)
        ns=node.newNs(SASL_NS,None)
        node.setNs(ns)
        if content:
            node.setContent(content)
        if isinstance(r,sasl.Failure):
            node.newChild(ns,r.reason,None)

        self._write_raw(node.serialize(encoding="UTF-8"))
        node.unlinkNode()
        node.freeNode()

        if isinstance(r,sasl.Success):
            if r.authzid:
                self.peer=JID(r.authzid)
            else:
                self.peer=JID(r.username,self.me.domain)
            self.peer_authenticated=1
            self.state_change("authenticated",self.peer)
            self._post_auth()

        if isinstance(r,sasl.Failure):
            raise SASLAuthenticationFailed,"SASL authentication failed"

        return True

    def _process_sasl_challenge(self,content):
        """Process incoming <sasl:challenge/> element.

        [initiating entity only]

        :Parameters:
            - `content`: the challenge data received (Base64-encoded).
        """
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL challenge")
            return False

        r=self.authenticator.challenge(base64.decodestring(content))
        if isinstance(r,sasl.Response):
            el_name="response"
            content=r.base64()
        else:
            el_name="abort"
            content=None

        root=self.doc_out.getRootElement()
        node=root.newChild(None,el_name,None)
        ns=node.newNs(SASL_NS,None)
        node.setNs(ns)
        if content:
            node.setContent(content)

        self._write_raw(node.serialize(encoding="UTF-8"))
        node.unlinkNode()
        node.freeNode()

        if isinstance(r,sasl.Failure):
            raise SASLAuthenticationFailed,"SASL authentication failed"

        return True

    def _process_sasl_response(self,content):
        """Process incoming <sasl:response/> element.

        [receiving entity only]

        :Parameters:
            - `content`: the response data received (Base64-encoded).
        """
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL response")
            return 0

        r=self.authenticator.response(base64.decodestring(content))
        if isinstance(r,sasl.Success):
            el_name="success"
            content=r.base64()
        elif isinstance(r,sasl.Challenge):
            el_name="challenge"
            content=r.base64()
        else:
            el_name="failure"
            content=None

        root=self.doc_out.getRootElement()
        node=root.newChild(None,el_name,None)
        ns=node.newNs(SASL_NS,None)
        node.setNs(ns)
        if content:
            node.setContent(content)
        if isinstance(r,sasl.Failure):
            node.newChild(ns,r.reason,None)

        self._write_raw(node.serialize(encoding="UTF-8"))
        node.unlinkNode()
        node.freeNode()

        if isinstance(r,sasl.Success):
            authzid=r.authzid
            if authzid:
                self.peer=JID(r.authzid)
            else:
                self.peer=JID(r.username,self.me.domain)
            self.peer_authenticated=1
            self._restart_stream()
            self.state_change("authenticated",self.peer)
            self._post_auth()

        if isinstance(r,sasl.Failure):
            raise SASLAuthenticationFailed,"SASL authentication failed"

        return 1

    def _process_sasl_success(self,content):
        """Process incoming <sasl:success/> element.

        [initiating entity only]

        :Parameters:
            - `content`: the "additional data with success" received (Base64-encoded).
        """
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL response")
            return False

        r=self.authenticator.finish(base64.decodestring(content))
        if isinstance(r,sasl.Success):
            self.__logger.debug("SASL authentication succeeded")
            if r.authzid:
                self.me=JID(r.authzid)
            else:
                self.me=self.me
            self.authenticated=1
            self._restart_stream()
            self.state_change("authenticated",self.me)
            self._post_auth()
        else:
            self.__logger.debug("SASL authentication failed")
            raise SASLAuthenticationFailed,"Additional success data procesing failed"
        return True

    def _process_sasl_failure(self,node):
        """Process incoming <sasl:failure/> element.

        [initiating entity only]

        :Parameters:
            - `node`: the XML node received.
        """
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL response")
            return False

        self.__logger.debug("SASL authentication failed: %r" % (node.serialize(),))
        raise SASLAuthenticationFailed,"SASL authentication failed"

    def _process_sasl_abort(self):
        """Process incoming <sasl:abort/> element.

        [receiving entity only]"""
        if not self.authenticator:
            self.__logger.debug("Unexpected SASL response")
            return False

        self.authenticator=None
        self.__logger.debug("SASL authentication aborted")
        return True

    def _sasl_authenticate(self,username,authzid,mechanism=None):
        """Start SASL authentication process.

        [initiating entity only]
        
        :Parameters:
            - `username`: user name.
            - `authzid`: authorization ID.
            - `mechanism`: SASL mechanism to use."""
        if not self.initiator:
            raise SASLAuthenticationFailed,"Only initiating entity start SASL authentication"
        while not self.features:
            self.__logger.debug("Waiting for features")
            self._read()
        if not self.peer_sasl_mechanisms:
            raise SASLNotAvailable,"Peer doesn't support SASL"

        if not mechanism:
            mechanism=None
            for m in self.sasl_mechanisms:
                if m in self.peer_sasl_mechanisms:
                    mechanism=m
                    break
            if not mechanism:
                raise SASLMechanismNotAvailable,"Peer doesn't support any of our SASL mechanisms"
            self.__logger.debug("Our mechanism: %r" % (mechanism,))
        else:
            if mechanism not in self.peer_sasl_mechanisms:
                raise SASLMechanismNotAvailable,"%s is not available" % (mechanism,)

        self.auth_method_used="sasl:"+mechanism

        self.authenticator=sasl.client_authenticator_factory(mechanism,self)

        initial_response=self.authenticator.start(username,authzid)
        if not isinstance(initial_response,sasl.Response):
            raise SASLAuthenticationFailed,"SASL initiation failed"

        root=self.doc_out.getRootElement()
        node=root.newChild(None,"auth",None)
        ns=node.newNs(SASL_NS,None)
        node.setNs(ns)
        node.setProp("mechanism",mechanism)
        if initial_response.data:
            node.setContent(initial_response.base64())

        self._write_raw(node.serialize(encoding="UTF-8"))
        node.unlinkNode()
        node.freeNode()

# vi: sts=4 et sw=4
