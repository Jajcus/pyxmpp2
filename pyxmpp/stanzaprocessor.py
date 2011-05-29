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
from abc import ABCMeta
import inspect

from .expdict import ExpiringDictionary
from .exceptions import ProtocolError, BadRequestProtocolError
from .exceptions import FeatureNotImplementedProtocolError
from .stanza import Stanza
from .message import Message
from .presence import Presence
from .stanzapayload import StanzaPayload, XMLPayload
from .iq import Iq

logger = logging.getLogger("pyxmpp.stanzaprocessor")


class XMPPFeatureHandler:
    __metaclass__ = ABCMeta

def _iq_handler(iq_type, payload_class, payload_key, usage_restriction):
    """Method decorator generator for decorating <iq type='get'/> stanza
    handler methods in `XMPPFeatureHandler` subclasses.
    
    :Parameters:
        - `payload_class`: payload class expected
        - `payload_key`: payload class specific filtering key
        - `usage_restriction`: optional usage restriction: "pre-auth" or
          "post-auth"
    :Types:
        - `payload_class`: subclass of `StanzaPayload`
        - `usage_restriction`: `unicode`
    """
    def decorator(func):
        """The decorator"""
        func._pyxmpp_stanza_handled = ("iq", iq_type)
        func._pyxmpp_payload_class_handled = payload_class
        func._pyxmpp_payload_key = payload_key
        func._pyxmpp_usage_restriction = usage_restriction
        return func
    return decorator


def iq_get_stanza_handler(payload_class, payload_key = None, 
                                            usage_restriction = "post-auth"):
    """Method decorator generator for decorating <iq type='get'/> stanza
    handler methods in `XMPPFeatureHandler` subclasses.
    
    :Parameters:
        - `payload_class`: payload class expected
        - `payload_key`: payload class specific filtering key
        - `usage_restriction`: optional usage restriction: "pre-auth" or
          "post-auth"
    :Types:
        - `payload_class`: subclass of `StanzaPayload`
        - `usage_restriction`: `unicode`
    """
    return _iq_handler("get", payload_class, payload_key, usage_restriction)

def iq_set_stanza_handler(payload_class, payload_key = None, 
                                            usage_restriction = "post-auth"):
    """Method decorator generator for decorating <iq type='set'/> stanza
    handler methods in `XMPPFeatureHandler` subclasses.
    
    :Parameters:
        - `payload_class`: payload class expected
        - `payload_key`: payload class specific filtering key
        - `usage_restriction`: optional usage restriction: "pre-auth" or
          "post-auth"
    :Types:
        - `payload_class`: subclass of `StanzaPayload`
        - `usage_restriction`: `unicode`
    """
    return _iq_handler("set", payload_class, payload_key, usage_restriction)

def _stanza_handler(element_name, stanza_type, payload_class, payload_key,
                                                            usage_restriction):
    """Method decorator generator for decorating <message/> or <presence/>
    stanza handler methods in `XMPPFeatureHandler` subclasses.
    
    :Parameters:
        - `element_name`: "message" or "presence"
        - `stanza_type`: expected value of the 'type' attribute of the stanza
        - `payload_class`: payload class expected
        - `payload_key`: payload class specific filtering key
        - `usage_restriction`: optional usage restriction: "pre-auth" or
          "post-auth"
    :Types:
        - `element_name`: `unicode`
        - `stanza_type`: `unicode`
        - `payload_class`: subclass of `StanzaPayload`
        - `usage_restriction`: `unicode`
    """
    def decorator(func):
        """The decorator"""
        func._pyxmpp_stanza_handled = (element_name, stanza_type)
        func._pyxmpp_payload_class_handled = payload_class
        func._pyxmpp_payload_key = payload_key
        func._pyxmpp_usage_restriction = usage_restriction
        return func
    return decorator

def message_stanza_handler(stanza_type = None, payload_class = None,
                            payload_key = None, usage_restriction = "post-auth"):
    """Method decorator generator for decorating <message/> 
    stanza handler methods in `XMPPFeatureHandler` subclasses.
    
    :Parameters:
        - `payload_class`: payload class expected
        - `stanza_type`: expected value of the 'type' attribute of the stanza.
          `None` means all types except 'error'
        - `payload_key`: payload class specific filtering key
        - `usage_restriction`: optional usage restriction: "pre-auth" or
          "post-auth"
    :Types:
        - `payload_class`: subclass of `StanzaPayload`
        - `stanza_type`: `unicode`
        - `usage_restriction`: `unicode`
    """
    if stanza_type is None:
        stanza_type = "normal"
    return _stanza_handler("message", stanza_type, payload_class, payload_key,
                                                            usage_restriction)
 
def presence_stanza_handler(stanza_type = None, payload_class = None,
                            payload_key = None, usage_restriction = "post-auth"):
    """Method decorator generator for decorating <presence/> 
    stanza handler methods in `XMPPFeatureHandler` subclasses.
    
    :Parameters:
        - `payload_class`: payload class expected
        - `stanza_type`: expected value of the 'type' attribute of the stanza.
        - `payload_key`: payload class specific filtering key
        - `usage_restriction`: optional usage restriction: "pre-auth" or
          "post-auth"
    :Types:
        - `payload_class`: subclass of `StanzaPayload`
        - `stanza_type`: `unicode`
        - `usage_restriction`: `unicode`
    """
    return _stanza_handler("presence", stanza_type, payload_class, payload_key,
                                                            usage_restriction)
 

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

    def _process_handler_result(self, response):
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
            else:
                logger.warning(u"Unexpected object in stanza handler result:"
                                                    u" {0!r}".format(stanza))
        return True

    def _process_iq_response(self, stanza):
        """Process IQ stanza of type 'response' or 'error'.

        :Parameters:
            - `stanza`: the stanza received
        :Types:
            - `stanza`: `Iq`

        If a matching handler is available pass the stanza to it.  Otherwise
        ignore it if it is "error" or "result" stanza or return
        "feature-not-implemented" error if it is "get" or "set".
        """
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
        self._process_handler_result(response)
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
        if typ not in ("get", "set"):
            raise BadRequestProtocolError("Bad <iq/> type")
        logger.debug("Handling <iq type='{0}'> stanza: {1!r}".format(
                                                            stanza, typ))
        payload = stanza.get_payload(None)
        logger.debug("  payload: {0!r}".format(payload))
        if not payload:
            raise BadRequestProtocolError("<iq/> stanza with no child element")
        handler = self._get_iq_handler(typ, payload)
        if not handler:
            payload = stanza.get_payload(None, specialize = True)
            logger.debug("  specialized payload: {0!r}".format(payload))
            if not isinstance(payload, XMLPayload):
                handler = self._get_iq_handler(typ, payload)
        if handler:
            response = handler(stanza)
            self._process_handler_result(response)
            return True
        else:
            raise FeatureNotImplementedProtocolError("Not implemented")

    def _get_iq_handler(self, iq_type, payload):
        """Get an <iq/> handler for given iq  type and payload."""
        key = (payload.__class__, payload.handler_key)
        logger.debug("looking up iq {0} handler for {1!r}, key: {2!r}"
                            .format(iq_type, payload, key))
        logger.debug("handlers: {0!r}".format(self._iq_handlers))
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
        for handler in handler_list:
            type_filter = handler._pyxmpp_stanza_handled[1]
            class_filter = handler._pyxmpp_payload_class_handled
            extra_filter = handler._pyxmpp_payload_key
            if type_filter != stanza_type:
                continue
            if class_filter:
                if extra_filter is None and class_filter not in classes:
                    continue
                if extra_filter and (class_filter, extra_filter) not in keys:
                    continue
            response = handler(stanza)
            if self._process_handler_result(response):
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

    def setup_stanza_handlers(self, handler_objects, usage_restriction):
        """Install stanza handlers provided by `handler_objects`"""
        iq_handlers = {"get": {}, "set": {}}
        message_handlers = []
        presence_handlers = []
        for obj in handler_objects:
            if not isinstance(obj, XMPPFeatureHandler):
                continue
            for name, handler in inspect.getmembers(obj, callable):
                if not hasattr(handler, "_pyxmpp_stanza_handled"):
                    continue
                element_name, stanza_type = handler._pyxmpp_stanza_handled
                restr = handler._pyxmpp_usage_restriction
                if restr and restr != usage_restriction:
                    continue
                if element_name == "iq":
                    payload_class = handler._pyxmpp_payload_class_handled
                    payload_key = handler._pyxmpp_payload_key
                    if (payload_class,payload_key) in iq_handlers[stanza_type]:
                        continue
                    iq_handlers[stanza_type][(payload_class,payload_key)] = \
                            handler
                    continue
                elif element_name == "message":
                    handler_list = message_handlers
                elif element_name == "presence":
                    handler_list = presence_handlers
                else:
                    raise ValueError, "Bad handler decoration"
                handler_list.append(handler)
        with self.lock:
            self._iq_handlers = iq_handlers
            self._presence_handlers = presence_handlers
            self._message_handlers = message_handlers

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
