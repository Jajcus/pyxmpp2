#
# (C) Copyright 2003-2010 Jacek Konieczny <jajcus@jajcus.net>
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

"""Handling of XMPP stanzas.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

import logging
import threading
from collections import defaultdict

from .expdict import ExpiringDictionary
from .exceptions import ProtocolError, BadRequestProtocolError
from .exceptions import FeatureNotImplementedProtocolError
from .stanza import Stanza
from .message import Message
from .presence import Presence
from .iq import Iq

logger = logging.getLogger("pyxmpp.stanzaprocessor")

def stanza_factory(element, stream = None, language = None):
    """Creates Iq, Message or Presence object for XML stanza `element`
    
    :Parameters:
        - `element`: the stanza XML element
        - `stream`: stream where the stanza was received
        - `language`: default language for the stanza
    :Types:
        - `element`: `ElementTree.Element`
        - `stream`: `pyxmpp2.stream.Stream`
        - `language`: `unicode`
    """
    tag = element.tag
    if tag.endswith("}iq") or tag == "iq":
        return Iq(element, stream = stream, language = language)
    if tag.endswith("}message") or tag == "message":
        return Message(element, stream = stream, language = language)
    if tag.endswith("}presence") or tag == "presence":
        return Presence(element, stream = stream, language = language)
    else:
        return Stanza(element, stream = stream, language = language)

class StanzaProcessor(object):
    """Universal stanza handler/router class.

    Provides facilities to set up custom handlers for various types of stanzas.

    :Ivariables:
        - `lock`: lock object used to synchronize access to the
          `StanzaProcessor` object.
        - `me`: local JID.
        - `peer`: remote stream endpoint JID.
        - `process_all_stanzas`: when `True` then all stanzas received are
          considered local.
        - `initiator`: `True` if local stream endpoint is the initiating entity.
    """
    # pylint: disable-msg=R0902
    def __init__(self, default_timeout = 300):
        """Initialize a `StanzaProcessor` object.

        :Parameters:
            - `default_timeout`: default timeout for IQ response handlers
        """
        self.me = None
        self.peer = None
        self.initiator = None
        self.peer_authenticated = False
        self.process_all_stanzas = True
        self._iq_response_handlers = ExpiringDictionary(default_timeout)
        self._iq_handlers = defaultdict(dict)
        self._message_handlers = []
        self._presence_handlers = []
        self.lock = threading.RLock()

    def process_response(self, response):
        """Examines out the response returned by a stanza handler and sends all
        stanzas provided.

        :Parameters:
            - `response`: the response to process. `None` or `False` means
            'not handled'. `True` means 'handled'. Stanza or stanza list means
            handled with the stanzas to send back
        :Types:
            - `response`: `bool` or `Stanza` or iterable of `Stanza`

        :Returns:
            - `True`: if `response` is `Stanza`, iterable or `True` (meaning the
             stanza was processed).
            - `False`: when `response` is `False` or `None`

        :returntype: `bool`
        """

        if response is None or response is False:
            return False

        if isinstance(response, Stanza):
            self.send(response)
            return True

        try:
            response = iter(response)
        except TypeError:
            return bool(response)

        for stanza in response:
            if isinstance(stanza, Stanza):
                self.send(stanza)
        return True

    def _process_iq_response(self, stanza):
        """Process IQ stanza of type 'response' or 'error'.

        :Parameters:
            - `stanza`: the stanza received
        :Types:
            - `stanza`: `Iq`

        If a matching handler is available pass the stanza to it.  Otherwise
        ignore it if it is "error" or "result" stanza or return
        "feature-not-implemented" error if it is "get" or "set"."""


        stanza_id = stanza.stanza_id
        from_jid = stanza.from_jid
        if from_jid:
            ufrom = from_jid.as_unicode()
        else:
            ufrom = None
        res_handler = err_handler = None
        try:
            res_handler, err_handler = self._iq_response_handlers.pop(
                                                    (stanza_id, ufrom))
        except KeyError:
            if ( (from_jid == self.peer or from_jid == self.me 
                                        or from_jid == self.me.bare()) ):
                try:
                    res_handler, err_handler = \
                            self._iq_response_handlers.pop(
                                                    (stanza_id, None))
                except KeyError:
                    pass
        if stanza.stanza_type == "result":
            if res_handler:
                response = res_handler(stanza)
            else:
                return False
        else:
            if err_handler:
                response = err_handler(stanza)
            else:
                return False
        self.process_response(response)
        return True

    def process_iq(self, stanza):
        """Process IQ stanza received.

        :Parameters:
            - `stanza`: the stanza received
        :Types:
            - `stanza`: `Iq`

        If a matching handler is available pass the stanza to it.  Otherwise
        ignore it if it is "error" or "result" stanza or return
        "feature-not-implemented" error if it is "get" or "set"."""

        typ = stanza.stanza_type
        if typ in ("result", "error"):
            return self._process_iq_response(stanza)
        payload = stanza.get_payload()
        if not payload:
            raise BadRequestProtocolError("<iq/> stanza with no child element")
        if typ == "get":
            handler = self._get_iq_handler("get", payload)
            if handler:
                response = handler(stanza)
                self.process_response(response)
                return True
            else:
                raise FeatureNotImplementedProtocolError("Not implemented")
        elif typ == "set":
            handler = self._get_iq_handler("set", payload)
            if handler:
                response = handler(stanza)
                self.process_response(response)
                return True
            else:
                raise FeatureNotImplementedProtocolError("Not implemented")
        else:
            raise BadRequestProtocolError("Unknown IQ stanza type")

    def _get_iq_handler(self, iq_type, payload):
        """Get an <iq/> handler for given iq  type and payload."""
        key = (payload.__class__, payload.handler_key)
        handler = self._iq_handlers[iq_type].get(key)
        return handler

    def __try_handlers(self, handler_list, stanza, stanza_type = None):
        """ Search the handler list for handlers matching
        given stanza type and payload namespace. Run the
        handlers found ordering them by priority until
        the first one which returns `True`.

        :Parameters:
            - `handler_list`: list of available handlers
            - `stanza`: the stanza to handle
            - `stanza_type`: stanza type override (value of its "type"
                            attribute)

        :return: result of the last handler or `False` if no
            handler was found."""
        if stanza_type is None:
            stanza_type = stanza.stanza_type
        payload = stanza.get_all_payload()
        classes = [p.__class__ for p in payload]
        keys = [(p.__class__, p.handler_key) for p in payload]
        for handler_entry in handler_list:
            type_filter = handler_entry[1]
            class_filter = handler_entry[2]
            extra_filter = handler_entry[3]
            handler = handler_entry[4]
            if type_filter != stanza_type:
                continue
            if class_filter:
                if extra_filter is None and class_filter not in classes:
                    continue
                if extra_filter and (class_filter, extra_filter) not in keys:
                    continue
            response = handler(stanza)
            if self.process_response(response):
                return True
        return False

    def process_message(self, stanza):
        """Process message stanza.

        Pass it to a handler of the stanza's type and payload namespace.
        If no handler for the actual stanza type succeeds then hadlers
        for type "normal" are used.

        :Parameters:
            - `stanza`: message stanza to be handled
        """

        if not self.initiator and not self.peer_authenticated:
            logger.debug("Ignoring message - peer not authenticated yet")
            return True


        stanza_type = stanza.stanza_type
        if stanza_type is None:
            stanza_type = "normal"

        if self.__try_handlers(self._message_handlers, stanza,
                                                stanza_type = stanza_type):
            return True

        if stanza_type not in ("error", "normal"):
            # try 'normal' handler additionaly to the regular handler
            return self.__try_handlers(self._message_handlers, stanza,
                                                    stanza_type = "normal")
        return False

    def process_presence(self, stanza):
        """Process presence stanza.

        Pass it to a handler of the stanza's type and payload namespace.

        :Parameters:
            - `stanza`: presence stanza to be handled
        """

        if not self.initiator and not self.peer_authenticated:
            logger.debug("Ignoring presence - peer not authenticated yet")
            return True

        stanza_type = stanza.stanza_type
        if not stanza_type:
            stanza_type = "available"
        return self.__try_handlers(self._presence_handlers, stanza, stanza_type)

    def route_stanza(self, stanza):
        """Process stanza not addressed to us.

        Return "recipient-unavailable" return if it is not
        "error" nor "result" stanza.

        This method should be overriden in derived classes if they
        are supposed to handle stanzas not addressed directly to local
        stream endpoint.

        :Parameters:
            - `stanza`: presence stanza to be processed
        """
        if stanza.stanza_type not in ("error", "result"):
            response = stanza.make_error_response(u"recipient-unavailable")
            self.send(response)
        return True

    def process_stanza(self, stanza):
        """Process stanza received from the stream.

        First "fix" the stanza with `self.fix_in_stanza()`,
        then pass it to `self.route_stanza()` if it is not directed
        to `self.me` and `self.process_all_stanzas` is not True. Otherwise
        stanza is passwd to `self.process_iq()`, `self.process_message()`
        or `self.process_presence()` appropriately.

        :Parameters:
            - `stanza`: the stanza received.

        :returns: `True` when stanza was handled
        """

        self.fix_in_stanza(stanza)
        to_jid = stanza.to_jid

        if not self.process_all_stanzas and to_jid and (
                to_jid != self.me and to_jid.bare() != self.me.bare()):
            return self.route_stanza(stanza)

        try:
            if isinstance(stanza, Iq):
                if self.process_iq(stanza):
                    return True
            elif isinstance(stanza, Message):
                if self.process_message(stanza):
                    return True
            elif isinstance(stanza, Presence):
                if self.process_presence(stanza):
                    return True
        except ProtocolError, err:
            typ = stanza.stanza_type
            if typ != 'error' and (typ != 'result' 
                                                or stanza.stanza_type != 'iq'):
                response = stanza.make_error_response(err.xmpp_name)
                self.send(response)
                err.log_reported()
            else:
                err.log_ignored()
            return
        logger.debug("Unhandled %r stanza: %r" % (stanza.stanza_type,
                                                        stanza.serialize()))
        return False

    def check_to(self, to_jid):
        """Check "to" attribute of received stream header.

        :return: `to_jid` if it is equal to `self.me`, None otherwise.

        Should be overriden in derived classes which require other logic
        for handling that attribute."""
        if to_jid != self.me:
            return None
        return to_jid

    def set_response_handlers(self, stanza, res_handler, err_handler,
                                    timeout_handler = None, timeout = None):
        """Set response handler for an IQ "get" or "set" stanza.

        This should be called before the stanza is sent.

        :Parameters:
            - `iq`: an IQ stanza
            - `res_handler`: result handler for the stanza. Will be called
              when matching <iq type="result"/> is received. Its only
              argument will be the stanza received. The handler may return
              a stanza or list of stanzas which should be sent in response.
            - `err_handler`: error handler for the stanza. Will be called
              when matching <iq type="error"/> is received. Its only
              argument will be the stanza received. The handler may return
              a stanza or list of stanzas which should be sent in response
              but this feature should rather not be used (it is better not to
              respond to 'error' stanzas).
            - `timeout_handler`: timeout handler for the stanza. Will be called
              (with no arguments) when no matching <iq type="result"/> or <iq
              type="error"/> is received in next `timeout` seconds.
            - `timeout`: timeout value for the stanza. After that time if no
              matching <iq type="result"/> nor <iq type="error"/> stanza is
              received, then timeout_handler (if given) will be called.
        """
        # pylint: disable-msg=R0913
        self.lock.acquire()
        try:
            self._set_response_handlers(stanza, res_handler, err_handler,
                                                    timeout_handler, timeout)
        finally:
            self.lock.release()

    def _set_response_handlers(self, stanza, res_handler, err_handler,
                                timeout_handler = None, timeout = None):
        """Same as `Stream.set_response_handlers` but assume `self.lock` is
        acquired."""
        # pylint: disable-msg=R0913
        self.fix_out_stanza(stanza)
        to_jid = stanza.to_jid
        if to_jid:
            to_jid = unicode(to_jid)
        if timeout_handler:
            def callback(dummy1, dummy2):
                """Wrapper for the timeout handler to make it compatible
                with the `ExpiringDictionary` """
                timeout_handler()
            self._iq_response_handlers.set_item(
                                    (stanza.stanza_id, to_jid),
                                    (res_handler,err_handler),
                                    timeout, callback)
        else:
            self._iq_response_handlers.set_item(
                                    (stanza.stanza_id, to_jid),
                                    (res_handler, err_handler),
                                    timeout)

    def set_iq_get_handler(self, payload_class, handler, payload_key = None):
        """Set <iq type="get"/> handler.

        :Parameters:
            - `payload_class`: payload class requested
            - `payload_key`: extra filter for payload
            - `handler`: function to be called when a stanza
              with defined element is received. Its only argument
              will be the stanza received. The handler may return a stanza or
              list of stanzas which should be sent in response.
        :Types:
            - `payload_class`: `classobj`, a subclass of `StanzaPayload`

        Only one handler may be defined per one namespaced element.
        If a handler for the element was already set it will be lost
        after calling this method.
        """
        self.lock.acquire()
        try:
            key = (payload_class, payload_key)
            self._iq_handlers["get"][key] = handler
        finally:
            self.lock.release()

    def unset_iq_get_handler(self, payload_class, payload_key):
        """Remove <iq type="get"/> handler.

        :Parameters:
            - `element`: payload element name
            - `namespace`: payload element namespace URI
        """
        self.lock.acquire()
        try:
            key = (payload_class, payload_key)
            if key in self._iq_handlers["get"]:
                del self._iq_handlers["get"][key]
        finally:
            self.lock.release()

    def set_iq_set_handler(self, payload_class, handler, payload_key = None):
        """Set <iq type="set"/> handler.

        :Parameters:
            - `payload_class`: payload class requested
            - `payload_key`: extra filter for payload
            - `handler`: function to be called when a stanza
              with defined element is received. Its only argument
              will be the stanza received. The handler may return a stanza or
              list of stanzas which should be sent in response.
        :Types:
            - `payload_class`: `classobj`, a subclass of `StanzaPayload`

        Only one handler may be defined per one namespaced element.
        If a handler for the element was already set it will be lost
        after calling this method.
        """
        self.lock.acquire()
        try:
            key = (payload_class, payload_key)
            self._iq_handlers["set"][key] = handler
        finally:
            self.lock.release()

    def unset_iq_set_handler(self, payload_class, payload_key):
        """Remove <iq type="set"/> handler.

        :Parameters:
            - `element`: payload element name
            - `namespace`: payload element namespace URI
        """
        self.lock.acquire()
        try:
            key = (payload_class, payload_key)
            if key in self._iq_handlers["set"]:
                del self._iq_handlers["set"][key]
        finally:
            self.lock.release()

    @staticmethod
    def __add_handler(handler_list, stanza_type, payload_class,
                                        payload_key, priority, handler):
        """Add a handler function to a prioritized handler list.

        :Parameters:
            - `handler_list`: a handler list.
            - `stanza_type`: stanza type.
            - `payload_class`: expected payload class. The handler will be
              called only for stanzas with payload of this class
            - `payload_key`: additional filter for the payload, specific
              for the `payload_class`
            - `priority`: handler priority. Must be >=0 and <=100. Handlers
              with lower priority list will be tried first."""
        # pylint: disable-msg=R0913
        if priority < 0 or priority > 100:
            raise ValueError("Bad handler priority (must be in 0:100)")
        handler_list.append((priority, stanza_type, payload_class, 
                                                payload_key, handler))
        handler_list.sort(key = lambda x: x[0])

    def set_message_handler(self, stanza_type, handler, payload_class = None,
                                        payload_key = None, priority=100):
        """Set a handler for <message/> stanzas.

        :Parameters:
            - `stanza_type`: message type. `None` will be treated the same as
              "normal", and will be the default for unknown types (those that
              have no handler associated).
            - `payload_class`: expected payload class. The handler will be
              called only for stanzas with payload of this class
            - `payload_key`: additional filter for the payload, specific
              for the `payload_class`
            - `priority`: priority value for the handler. Handlers with lower
              priority value are tried first.
            - `handler`: function to be called when a message stanza
              with defined type and payload namespace is received. Its only
              argument will be the stanza received. The handler may return a
              stanza or list of stanzas which should be sent in response.

        Multiple <message /> handlers with the same type/namespace/priority may
        be set. Order of calling handlers with the same priority is not
        defined.  Handlers will be called in priority order until one of them
        returns True or any stanza(s) to send (even empty list will do).
        """
        # pylint: disable-msg=R0913
        self.lock.acquire()
        try:
            if stanza_type is None:
                stanza_type = "normal"
            self.__add_handler(self._message_handlers, stanza_type, 
                                        payload_class, payload_key,
                                        priority, handler)
        finally:
            self.lock.release()

    def set_presence_handler(self, stanza_type, handler, payload_class = None,
                                    payload_key = None, priority = 100):
        """Set a handler for <presence/> stanzas.

        :Parameters:
            - `stanza_type`: presence type. "available" will be treated the
              same as `None`.
            - `handler`: function to be called when a presence stanza
              with defined type and payload namespace is received. Its only
              argument will be the stanza received. The handler may return a
              stanza or list of stanzas which should be sent in response.
            - `payload_class`: expected payload class. If given, then the
              handler will be called only for stanzas with payload of this
              class
            - `payload_key`: additional filter for the payload, specific
              for the `payload_class`
            - `priority`: priority value for the handler. Handlers with lower
              priority value are tried first.

        Multiple <presence /> handlers with the same type/class/filter/priority
        may be set. Order of calling handlers with the same priority is not
        defined.  Handlers will be called in priority order until one of them
        returns True or any stanza(s) to send (even empty list will do).
        """
        # pylint: disable-msg=R0913
        self.lock.acquire()
        try:
            if not stanza_type:
                stanza_type = "available"
            self.__add_handler(self._presence_handlers, stanza_type,
                                    payload_class, payload_key,
                                    priority, handler)
        finally:
            self.lock.release()

    def fix_in_stanza(self, stanza):
        """Modify incoming stanza before processing it.

        This implementation does nothig. It should be overriden in derived
        classes if needed."""
        pass

    def fix_out_stanza(self, stanza):
        """Modify outgoing stanza before sending into the stream.

        This implementation does nothig. It should be overriden in derived
        classes if needed."""
        pass


    def send(self, stanza):
        """Send a stanza somwhere. This one does nothing. Should be overriden
        in derived classes.

        :Parameters:
            - `stanza`: the stanza to send.
        :Types:
            - `stanza`: `pyxmpp.stanza.Stanza`"""
        raise NotImplementedError("This method must be overriden in derived"
                                    " classes.")

# vi: sts=4 et sw=4
