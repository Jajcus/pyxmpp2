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

"""Presence XMPP stanza handling"""

__revision__="$Id: presence.py,v 1.21 2004/09/14 19:57:58 jajcus Exp $"
__docformat__="restructuredtext en"

import libxml2

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.stanza import Stanza,StanzaError

presence_types=("available","unavailable","subscribe","unsubscribe","subscribed",
        "unsubscribed","invisible","error")

accept_responses={
        "subscribe": "subscribed",
        "subscribed": "subscribe",
        "unsubscribe": "unsubscribed",
        "unsubscribed": "unsubscribe",
        }

deny_responses={
        "subscribe": "unsubscribed",
        "subscribed": "unsubscribe",
        "unsubscribe": "subscribed",
        "unsubscribed": "subscribe",
        }

class Presence(Stanza):
    """Wraper object for <presence /> stanzas."""
    stanza_type="presence"
    def __init__(self,node=None,fr=None,to=None,typ=None,sid=None,
            show=None,status=None,priority=0,error=None,error_cond=None):
        """Initialize a `Presence` object.

        :Parameters:
            - `node`: XML node to be wrapped into the `Presence` object
              or other Presence object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `fr`: sender JID.
            - `to`: recipient JID.
            - `typ`: staza type: one of: None, "available", "unavailable",
              "subscribe", "subscribed", "unsubscribe", "unsubscribed" or
              "error". "available" is automaticaly changed to None.
            - `sid`: stanza id -- value of stanza's "id" attribute
            - `show`: "show" field of presence stanza. One of: None, "away",
              "xa", "dnd", "chat".
            - `status`: descriptive text for the presence stanza.
            - `priority`: presence priority.
            - `error_cond`: error condition name. Ignored if `typ` is not "error" """
        self.node=None
        if isinstance(node,Presence):
            pass
        elif isinstance(node,Stanza):
            raise TypeError,"Couldn't make Presence from other Stanza"
        elif isinstance(node,libxml2.xmlNode):
            pass
        elif node is not None:
            raise TypeError,"Couldn't make Presence from %r" % (type(node),)

        if typ and typ not in presence_types:
            raise StanzaError,"Invalid presence type: %r" % (type,)

        if typ=="available":
            typ=None

        if node is None:
            node="presence"
            
        Stanza.__init__(self, node, fr=fr, to=to, typ=typ, sid=sid,
                error=error, error_cond=error_cond)
       
        if show:
            self.node.newTextChild(None,"show",to_utf8(show))
        if status:
            self.node.newTextChild(None,"status",to_utf8(status))
        if priority and priority!=0:
            self.node.newTextChild(None,"priority",to_utf8(str(priority)))

    def copy(self):
        """Create a deep copy of the presence stanza."""
        return Presence(self)

    def set_status(self,status):
        """Change presence status description.
        
        :Parameters:
            - `status`: descriptive text for the presence stanza."""
        n=self.xpath_eval("status")
        if not status:
            if n:
                n[0].unlinkNode()
                n[0].freeNode()
            else:
                return
        if n:
            n[0].setContent(to_utf8(status))
        else:
            self.node.newTextChild(None,"status",to_utf8(status))

    def get_status(self):
        """Get presence status description.
        
        :return: value of stanza's <status/> field."""
        n=self.xpath_eval("status")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def get_show(self):
        """Get presence "show" field.
        
        :return: value of stanza's <show/> field."""
        n=self.xpath_eval("show")
        if n:
            return from_utf8(n[0].getContent())
        else:
            return None

    def set_show(self,show):
        """Change presence "show" field.
        
        :Parameters:
            - `show`: new value for the "show" field of presence stanza. One
              of: None, "away", "xa", "dnd", "chat"."""
        n=self.xpath_eval("show")
        if not show:
            if n:
                n[0].unlinkNode()
                n[0].freeNode()
            else:
                return
        if n:
            n[0].setContent(to_utf8(show))
        else:
            self.node.newTextChild(None,"show",to_utf8(show))

    def get_priority(self):
        """Get presence priority.
        
        :return: value of stanza's priority. 0 if the stanza doesn't contain
            <priority/> element"""
        n=self.xpath_eval("priority")
        if not n:
            return 0
        try:
            prio=int(n[0].getContent())
        except ValueError:
            return 0
        return prio

    def set_priority(self,priority):
        """Change presence priority.
        
        :Parameters:
            - `priority`: new presence priority"""
        n=self.xpath_eval("priority")
        if not priority:
            if n:
                n[0].unlinkNode()
                n[0].freeNode()
            else:
                return
        priority=int(priority)
        if priority<-128 or priority>127:
            raise ValueError,"Bad priority value"
        priority=str(priority)
        if n:
            n[0].setContent(priority)
        else:
            self.node.newTextChild(None,"priority",priority)

    def make_accept_response(self):
        """Create "accept" response for the "subscribe"/"subscribed"/"unsubscribe"/"unsubscribed"
        presence stanza.

        :return: new `Presence` object."""

        if self.get_type() not in ("subscribe","subscribed","unsubscribe","unsubscribed"):
            raise StanzaError,("Results may only be generated for 'subscribe',"
                "'subscribed','unsubscribe' or 'unsubscribed' presence")

        pr=Presence(typ=accept_responses[self.get_type()],
            fr=self.get_to(),to=self.get_from(),sid=self.get_id())
        return pr

    def make_deny_response(self):
        """Create "deny" response for the "subscribe"/"subscribed"/"unsubscribe"/"unsubscribed"
        presence stanza.

        :return: new `Presence` object."""
        if self.get_type() not in ("subscribe","subscribed","unsubscribe","unsubscribed"):
            raise StanzaError,("Results may only be generated for 'subscribe',"
                "'subscribed','unsubscribe' or 'unsubscribed' presence")

        pr=Presence(typ=accept_responses[self.get_type()],
            fr=self.get_to(),to=self.get_from(),sid=self.get_id())
        return pr

    def make_error_response(self,cond):
        """Create error response for the any non-error presence stanza.

        :Parameters:
            - `cond`: error condition name, as defined in XMPP specification.

        :return: new `Presence` object."""
        
        if self.get_type() == "error":
            raise StanzaError,"Errors may not be generated in response to errors"

        p=Presence(typ="error",fr=self.get_to(),to=self.get_from(),
            sid=self.get_id(),error_cond=cond)

        if self.node.children:
            n=self.node.children
            while n:
                p.node.children.addPrevSibling(n.copyNode(1))
                n=n.next
        return p

# vi: sts=4 et sw=4
