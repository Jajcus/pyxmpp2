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

"""Delayed delivery mark (jabber:x:delay) handling"""

__revision__="$Id: delay.py,v 1.7 2004/09/10 14:01:01 jajcus Exp $"
__docformat__="restructuredtext en"

import sys
import libxml2
import time
import datetime
from types import StringType,UnicodeType

from pyxmpp.stanza import common_doc,common_root
from pyxmpp.jid import JID

from pyxmpp.utils import to_utf8,from_utf8,get_node_ns_uri,get_node_ns
from pyxmpp.utils import datetime_utc_to_local,datetime_local_to_utc

DELAY_NS="jabber:x:delay"

class Delay:
    """
    Delayed delivery tag.

    Represents 'jabber:x:delay' (JEP-0091) element of a Jabber stanza.

    Public attributes:
    fr - the "from" value of the delay element
    reason - the "reason" (content) of the delay element
    timestamp - the UTC timestamp as naive datetime object
    """

    def __init__(self,node_or_datetime,fr=None,reason=None,utc=True):
        """
        Initialize the Delay object.

        If `node_or_datetime` is an XML node it will be parsed,
        otherwise it should be a i`datetime.datetime` object containing the
        timestamp.

        When `node_or_datetime` is the timestamp value `fr` could be set
        to the "from" value of the Delay tag, and `reason` to an optional reason.

        The the timestamp is treated as UTC when `utc` is `True` or as a local time
        otherwise.
        """
        if isinstance(node_or_datetime,libxml2.xmlNode):
            self.from_xml(node_or_datetime)
        else:
            if utc:
                self.timestamp=node_or_datetime
            else:
                self.timestamp=datetime_local_to_utc(node_or_datetime)
            self.fr=JID(fr)
            self.reason=unicode(reason)

    def from_xml(self,node):
        """Initialize Delay object from XML node."""
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
        fr=node.prop("from")
        if fr:
            self.fr=JID(fr)
        else:
            self.fr=None
        self.reason=from_utf8(node.getContent())

    def as_xml(self,parent=None):
        """
        Return XML representation of the Delay object.

        If `parent` is given the item will be created as its child.
        The element will be standalone node in `common_doc` context otherwise.
        """
        if parent:
            node=parent.newTextChild(None,"x",None)
        else:
            node=common_doc.newDocNode(None,"x",None)
        ns=node.newNs(ROSTER_NS,None)
        node.setNs(ns)
        tm=self.timestamp.strftime("%Y%m%dT%H:%M:%S")
        node.setProp("stamp",tm)
        if self.fr:
            node.setProp("from",fr.as_utf8())
        if self.reason:
            node.setContent(to_utf8(self.reason))
        return node

    def datetime_local(self):
        """
        Returns datetime object representing the timestamp in local time.
        """
        r=datetime_utc_to_local(self.timestamp)
        return r

    def datetime_utc(self):
        """
        Returns datetime object representing the timestamp in UTC time.
        """
        return self.timestamp

    def __str__(self):
        n=self.as_xml()
        r=n.serialize()
        n.freeNode()
        return r

def get_delay(stanza):
        n=stanza.node.children
        while n:
            if n.type=="element" and get_node_ns_uri(n)==DELAY_NS and n.name=="x":
                return Delay(n)
            n=n.next
        return None

# vi: sts=4 et sw=4
