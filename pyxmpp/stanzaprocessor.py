#
# (C) Copyright 2003-2004 Jacek Konieczny <jajcus@jajcus.net>
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

__revision__="$Id$"
__docformat__="restructuredtext en"

import libxml2
import logging
import threading

from pyxmpp.expdict import ExpiringDictionary

class StanzaProcessor:
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
    def __init__(self):
        """Initialize a `StanzaProcessor` object."""
        self.me=None
        self.peer=None
        self.initiator=None
        self.peer_authenticated=False
        self.process_all_stanzas=True
        self._iq_response_handlers=ExpiringDictionary()
        self._iq_get_handlers={}
        self._iq_set_handlers={}
        self._message_handlers=[]
        self._presence_handlers=[]
        self.__logger=logging.getLogger("pyxmpp.Stream")
        self.lock=threading.RLock()

    def process_iq(self,stanza):
        """Process IQ stanza received.

        :Parameters:
            - `stanza`: the stanza received

        If a matching handler is available pass the stanza to it.
        Otherwise ignore it if it is "error" or "result" stanza
        or return "feature-not-implemented" error."""

        sid=stanza.get_id()
        fr=stanza.get_from()

        typ=stanza.get_type()
        if typ in ("result","error"):
            if fr:
                ufr=fr.as_unicode()
            else:
                ufr=None
            if self._iq_response_handlers.has_key((sid,ufr)):
                key=(sid,ufr)
            elif ( (fr==self.peer or fr==self.me)
                    and self._iq_response_handlers.has_key((sid,None))):
                key=(sid,None)
            else:
                return 0
            res_handler,err_handler=self._iq_response_handlers[key]
            if stanza.get_type()=="result":
                res_handler(stanza)
            else:
                err_handler(stanza)
            del self._iq_response_handlers[key]
            return 1

        q=stanza.get_query()
        if not q:
            r=stanza.make_error_response("bad-request")
            self.send(r)
            return 1
        el=q.name
        ns=q.ns().getContent()

        if typ=="get" and self._iq_get_handlers.has_key((el,ns)):
            self._iq_get_handlers[(el,ns)](stanza)
            return 1
        elif typ=="set" and self._iq_set_handlers.has_key((el,ns)):
            self._iq_set_handlers[(el,ns)](stanza)
            return 1
        else:
            r=stanza.make_error_response("feature-not-implemented")
            self.send(r)
            return 1

    def __try_handlers(self,handler_list,typ,stanza):
        """ Search the handler list for handlers matching
        given stanza type and payload namespace. Run the
        handlers found ordering them by priority until
        the first one which returns `True`.

        :Parameters:
            - `handler_list`: list of available handlers
            - `typ`: stanza type (value of its "type" attribute)
            - `stanza`: the stanza to handle

        :return: result of the last handler or `False` if no
            handler was found."""
        namespaces=[]
        if stanza.xmlnode.children:
            c=stanza.xmlnode.children
            while c:
                try:
                    ns=c.ns()
                except libxml2.treeError:
                    ns=None
                if ns is None:
                    c=c.next
                    continue
                ns_uri=ns.getContent()
                if ns_uri not in namespaces:
                    namespaces.append(ns_uri)
                c=c.next
        for handler_entry in handler_list:
            t=handler_entry[1]
            ns=handler_entry[2]
            handler=handler_entry[3]
            if t!=typ:
                continue
            if ns is not None and ns not in namespaces:
                continue
            if handler(stanza):
                return True
        return False

    def process_message(self,stanza):
        """Process message stanza.

        Pass it to a handler of the stanza's type and payload namespace.
        If no handler for the actual stanza type succeeds then hadlers
        for type "normal" are used.

        :Parameters:
            - `stanza`: message stanza to be handled
        """

        if not self.initiator and not self.peer_authenticated:
            self.__logger.debug("Ignoring message - peer not authenticated yet")
            return 1

        typ=stanza.get_type()
        if self.__try_handlers(self._message_handlers,typ,stanza):
            return 1
        if typ!="error":
            return self.__try_handlers(self._message_handlers,"normal",stanza)
        return 0

    def process_presence(self,stanza):
        """Process presence stanza.

        Pass it to a handler of the stanza's type and payload namespace.

        :Parameters:
            - `stanza`: presence stanza to be handled
        """

        if not self.initiator and not self.peer_authenticated:
            self.__logger.debug("Ignoring presence - peer not authenticated yet")
            return 1

        typ=stanza.get_type()
        if not typ:
            typ="available"
        return self.__try_handlers(self._presence_handlers,typ,stanza)

    def route_stanza(self,stanza):
        """Process stanza not addressed to us.

        Return "recipient-unavailable" return if it is not
        "error" nor "result" stanza.

        This method should be overriden in derived classes if they
        are supposed to handle stanzas not addressed directly to local
        stream endpoint.

        :Parameters:
            - `stanza`: presence stanza to be processed
        """
        if stanza.get_type() not in ("error","result"):
            r=stanza.make_error_response("recipient-unavailable")
            self.send(r)
        return 1

    def process_stanza(self,stanza):
        """Process stanza received from the stream.

        First "fix" the stanza with `self.fix_in_stanza()`,
        then pass it to `self.route_stanza()` if it is not directed
        to `self.me` and `self.process_all_stanzas` is not True. Otherwise
        stanza is passwd to `self.process_iq()`, `self.process_message()`
        or `self.process_presence()` appropriately.

        :Parameters:
            - `stanza`: the stanza received.
        """

        self.fix_in_stanza(stanza)
        to=stanza.get_to()

        if not self.process_all_stanzas and to and to!=self.me and to.bare()!=self.me.bare():
            return self.route_stanza(stanza)

        if stanza.stanza_type=="iq":
            if self.process_iq(stanza):
                return
        elif stanza.stanza_type=="message":
            if self.process_message(stanza):
                return
        elif stanza.stanza_type=="presence":
            if self.process_presence(stanza):
                return
        self.__logger.debug("Unhandled %r stanza: %r" % (stanza.stanza_type,stanza.serialize()))

    def check_to(self,to):
        """Check "to" attribute of received stream header.

        :return: `to` if it is equal to `self.me`, None otherwise.

        Should be overriden in derived classes which require other logic
        for handling that attribute."""
        if to!=self.me:
            return None
        return to

    def set_response_handlers(self,iq,res_handler,err_handler,timeout_handler=None,timeout=300):
        """Set response handler for an IQ "get" or "set" stanza.

        This should be called before the stanza is sent.

        :Parameters:
            - `iq`: an IQ stanza
            - `res_handler`: result handler for the stanza. Will be called
              when matching <iq type="result"/> is received. Its only
              argument will be the stanza received.
            - `err_handler`: error handler for the stanza. Will be called
              when matching <iq type="error"/> is received. Its only
              argument will be the stanza received.
            - `timeout_handler`: timeout handler for the stanza. Will be called
              when no matching <iq type="result"/> or <iq type="error"/> is
              received in next `timeout` seconds. The handler should accept
              two arguments and ignore them.
            - `timeout`: timeout value for the stanza. After that time if no
              matching <iq type="result"/> nor <iq type="error"/> stanza is
              received, then timeout_handler (if given) will be called.
        """
        self.lock.acquire()
        try:
            self._set_response_handlers(iq,res_handler,err_handler,timeout_handler,timeout)
        finally:
            self.lock.release()

    def _set_response_handlers(self,iq,res_handler,err_handler,timeout_handler=None,timeout=300):
        """Same as `Stream.set_response_handlers` but assume `self.lock` is acquired."""
        self.fix_out_stanza(iq)
        to=iq.get_to()
        if to:
            to=to.as_unicode()
        if timeout_handler:
            self._iq_response_handlers.set_item((iq.get_id(),to),
                    (res_handler,err_handler),
                    timeout,timeout_handler)
        else:
            self._iq_response_handlers.set_item((iq.get_id(),to),
                    (res_handler,err_handler),timeout)

    def set_iq_get_handler(self,element,namespace,handler):
        """Set <iq type="get"/> handler.

        :Parameters:
            - `element`: payload element name
            - `namespace`: payload element namespace URI
            - `handler`: function to be called when a stanza
              with defined element is received. Its only argument
              will be the stanza received.

        Only one handler may be defined per one namespaced element.
        If a handler for the element was already set it will be lost
        after calling this method.
        """
        self.lock.acquire()
        try:
            self._iq_get_handlers[(element,namespace)]=handler
        finally:
            self.lock.release()

    def unset_iq_get_handler(self,element,namespace):
        """Remove <iq type="get"/> handler.

        :Parameters:
            - `element`: payload element name
            - `namespace`: payload element namespace URI
        """
        self.lock.acquire()
        try:
            if self._iq_get_handlers.has_key((element,namespace)):
                del self._iq_get_handlers[(element,namespace)]
        finally:
            self.lock.release()

    def set_iq_set_handler(self,element,namespace,handler):
        """Set <iq type="set"/> handler.

        :Parameters:
            - `element`: payload element name
            - `namespace`: payload element namespace URI
            - `handler`: function to be called when a stanza
              with defined element is received. Its only argument
              will be the stanza received.

        Only one handler may be defined per one namespaced element.
        If a handler for the element was already set it will be lost
        after calling this method."""
        self.lock.acquire()
        try:
            self._iq_set_handlers[(element,namespace)]=handler
        finally:
            self.lock.release()

    def unset_iq_set_handler(self,element,namespace):
        """Remove <iq type="set"/> handler.

        :Parameters:
            - `element`: payload element name.
            - `namespace`: payload element namespace URI."""
        self.lock.acquire()
        try:
            if self._iq_set_handlers.has_key((element,namespace)):
                del self._iq_set_handlers[(element,namespace)]
        finally:
            self.lock.release()

    def __add_handler(self,handler_list,typ,namespace,priority,handler):
        """Add a handler function to a prioritized handler list.

        :Parameters:
            - `handler_list`: a handler list.
            - `typ`: stanza type.
            - `namespace`: stanza payload namespace.
            - `priority`: handler priority. Must be >=0 and <=100. Handlers
              with lower priority list will be tried first."""
        if priority<0 or priority>100:
            raise ValueError,"Bad handler priority (must be in 0:100)"
        handler_list.append((priority,typ,namespace,handler))
        handler_list.sort()

    def set_message_handler(self,typ,handler,namespace=None,priority=100):
        """Set a handler for <message/> stanzas.

        :Parameters:
            - `typ`: message type. `None` will be treated the same as "normal",
              and will be the default for unknown types (those that have no
              handler associated).
            - `namespace`: payload namespace. If `None` that message with any
              payload (or even with no payload) will match.
            - `priority`: priority value for the handler. Handlers with lower
              priority value are tried first.

        Multiple <message /> handlers with the same type/namespace/priority may
        be set. Order of calling handlers with the same priority is not defined.
        Handlers will be called in priority order until one of them returns True.
        """
        self.lock.acquire()
        try:
            if not typ:
                typ=="normal"
            self.__add_handler(self._message_handlers,typ,namespace,priority,handler)
        finally:
            self.lock.release()

    def set_presence_handler(self,typ,handler,namespace=None,priority=100):
        """Set a handler for <presence/> stanzas.

        :Parameters:
            - `typ`: presence type. `None` will be treated the same as "available".
            - `namespace`: payload namespace. If `None` that presence with any
              payload (or even with no payload) will match.
            - `priority`: priority value for the handler. Handlers with lower
              priority value are tried first.

        Multiple <presence /> handlers with the same type/namespace/priority may
        be set. Order of calling handlers with the same priority is not defined.
        Handlers will be called in priority order until one of them returns True.
        """
        self.lock.acquire()
        try:
            if not typ:
                typ="available"
            self.__add_handler(self._presence_handlers,typ,namespace,priority,handler)
        finally:
            self.lock.release()

    def fix_in_stanza(self,stanza):
        """Modify incoming stanza before processing it.

        This implementation does nothig. It should be overriden in derived
        classes if needed."""
        pass

    def fix_out_stanza(self,stanza):
        """Modify outgoing stanza before sending into the stream.

        This implementation does nothig. It should be overriden in derived
        classes if needed."""
        pass


    def send(self,stanza):
        """Send a stanza somwhere. This one does nothing. Should be overriden
        in derived classes.

        :Parameters:
            - `stanza`: the stanza to send.
        :Types:
            - `stanza`: `pyxmpp.stanza.Stanza`"""
        raise NotImplementedError,"This method must be overriden in derived classes."""


# vi: sts=4 et sw=4
