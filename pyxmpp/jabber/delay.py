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

"""Delayed delivery mark (jabber:x:delay) handling.

Normative reference:
  - `JEP 91 <http://www.jabber.org/jeps/jep-0091.html>`__
"""

__revision__="$Id$"
__docformat__="restructuredtext en"

import libxml2
import time
import datetime

from pyxmpp.stanza import common_doc
from pyxmpp.jid import JID

from pyxmpp.utils import to_utf8,from_utf8,get_node_ns_uri
from pyxmpp.utils import datetime_utc_to_local,datetime_local_to_utc

DELAY_NS="jabber:x:delay"

class Delay:
    """
    Delayed delivery tag.

    Represents 'jabber:x:delay' (JEP-0091) element of a Jabber stanza.

    :Ivariables:
        - `delay_from`: the "from" value of the delay element
        - `reason`: the "reason" (content) of the delay element
        - `timestamp`: the UTC timestamp as naive datetime object
    """

    def __init__(self,node_or_datetime,delay_from=None,reason=None,utc=True):
        """
        Initialize the Delay object.

        :Parameters:
            - `node_or_datetime`: an XML node to parse or the timestamp.
            - `delay_from`: JID of the entity which adds the delay mark
              (when `node_or_datetime` is a timestamp).
            - `reason`: reason of the delay (when `node_or_datetime` is a
              timestamp).
            - `utc`: if `True` then the timestamp is assumed to be UTC,
              otherwise it is assumed to be local time.
        :Types:
            - `node_or_datetime`: `libxml2.xmlNode` or `datetime.datetime`
            - `delay_from`: `pyxmpp.JID`
            - `reason`: `unicode`
            - `utc`: `bool`"""
        if isinstance(node_or_datetime,libxml2.xmlNode):
            self.from_xml(node_or_datetime)
        else:
            if utc:
                self.timestamp=node_or_datetime
            else:
                self.timestamp=datetime_local_to_utc(node_or_datetime)
            self.delay_from=JID(delay_from)
            self.reason=unicode(reason)

    def from_xml(self,node):
        """Initialize Delay object from an XML node.

        :Parameters:
            - `node`: the jabber:x:delay XML element.
        :Types:
            - `node`: `libxml2.xmlNode`"""
        if node.type!="element":
            raise ValueError,"XML node is not a jabber:x:delay element (not an element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=DELAY_NS or node.name!="x":
            raise ValueError,"XML node is not a jabber:x:delay element"
        stamp=node.prop("stamp")
        if stamp.endswith("Z"):
            stamp=stamp[:-1]
        if "-" in stamp:
            stamp=stamp.split("-",1)[0]
        tm=time.strptime(stamp,"%Y%m%dT%H:%M:%S")
        tm=tm[0:8]+(0,)
        self.timestamp=datetime.datetime.fromtimestamp(time.mktime(tm))
        delay_from=node.prop("from")
        if delay_from:
            self.delay_from=JID(delay_from)
        else:
            self.delay_from=None
        self.reason=from_utf8(node.getContent())

    def as_xml(self,parent=None):
        """
        Return XML representation of the Delay object.

        :Parameters:
            - `parent`: the parent node for the element to be created.
        :Types:
            - `parent`: `libxml2.xmlNode`

        If the `parent` is not given then the element will be standalone node
        in `pyxmpp.stanza.common_doc` context.

        :return: the XML element.
        :returntype: `libxml2.xmlNode`"""
        if parent:
            node=parent.newTextChild(None,"x",None)
        else:
            node=common_doc.newDocNode(None,"x",None)
        ns=node.newNs(DELAY_NS,None)
        node.setNs(ns)
        tm=self.timestamp.strftime("%Y%m%dT%H:%M:%S")
        node.setProp("stamp",tm)
        if self.delay_from:
            node.setProp("from",self.delay_from.as_utf8())
        if self.reason:
            node.setContent(to_utf8(self.reason))
        return node

    def datetime_local(self):
        """Get the timestamp as a local time.

        :return: the timestamp of the delay element represented in the local
          timezone.
        :returntype: `datetime.datetime`"""
        r=datetime_utc_to_local(self.timestamp)
        return r

    def datetime_utc(self):
        """Get the timestamp as a UTC.

        :return: the timestamp of the delay element represented in UTC.
        :returntype: `datetime.datetime`"""
        return self.timestamp

    def __str__(self):
        n=self.as_xml()
        r=n.serialize()
        n.freeNode()
        return r

    def __cmp__(self,other):
        return self.timestamp.__cmp__(other.timestamp)

def get_delays(stanza):
    """Get jabber:x:delay elements from the stanza.

    :Parameters:
        - `stanza`: a, probably delayed, stanza.
    :Types:
        - `stanza`: `pyxmpp.stanza.Stanza`

    :return: list of delay tags sorted by the timestamp.
    :returntype: `list` of `Delay`"""
    delays=[]
    n=stanza.node.children
    while n:
        if n.type=="element" and get_node_ns_uri(n)==DELAY_NS and n.name=="x":
            delays.append(Delay(n))
        n=n.next
    delays.sort()
    return delays

def get_delay(stanza):
    """Get the oldest jabber:x:delay elements from the stanza.

    :Parameters:
        - `stanza`: a, probably delayed, stanza.
    :Types:
        - `stanza`: `pyxmpp.stanza.Stanza`

    The return value, if not `None`, contains a quite reliable
    timestamp of a delayed (e.g. from offline storage) message.

    :return: the oldest delay tag of the stanza or `None`.
    :returntype: `Delay`"""
    delays=get_delays(stanza)
    if not delays:
        return None
    return get_delays(stanza)[0]

# vi: sts=4 et sw=4
