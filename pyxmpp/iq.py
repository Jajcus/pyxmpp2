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

"""Iq XMPP stanza handling"""

__revision__="$Id: iq.py,v 1.13 2004/09/13 21:14:53 jajcus Exp $"
__docformat__="restructuredtext en"

import libxml2

from pyxmpp.utils import get_node_ns_uri
from pyxmpp.stanza import Stanza,StanzaError,gen_id

class Iq(Stanza):
    """Wraper object for <iq /> stanzas."""
    stanza_type="iq"
    def __init__(self,node=None,fr=None,to=None,typ=None,sid=None,
            error=None,error_cond=None):
        """Initialize an `Iq` object.

        :Parameters:
            - `node`: XML node to be wrapped into the `Iq` object
              or other Presence object to be copied. If not given then new
              presence stanza is created using following parameters.
            - `fr`: sender JID.
            - `to`: recipient JID.
            - `typ`: staza type: one of: "get", "set", "result" or "error".
            - `sid`: stanza id -- value of stanza's "id" attribute. If not
              given, then unique for the session value is generated. 
            - `error_cond`: error condition name. Ignored if `typ` is not "error". """

        self.node=None
        if isinstance(node,Iq):
            pass
        elif isinstance(node,Stanza):
            raise TypeError,"Couldn't make Iq from other Stanza"
        elif isinstance(node,libxml2.xmlNode):
            pass
        elif node is not None:
            raise TypeError,"Couldn't make Iq from %r" % (type(node),)
        elif not typ:
            raise StanzaError,"type is required for Iq"
        else:
            if sid:
                sid=gen_id()

        if typ not in ("get","set","result","error"):
            raise StanzaError,"Invalid Iq type: %r" % (type,)

        if node is None:
            node="iq"

        Stanza.__init__(self, node, fr=fr, to=to, typ=typ, sid=sid,
                error=error, error_cond=error_cond)

    def copy(self):
        """Create a deep copy of the iq stanza."""
        return Iq(self)

    def make_error_response(self,cond):
        """Create error response for the a "get" or "set" iq stanza.

        :Parameters:
            - `cond`: error condition name, as defined in XMPP specification.

        :return: new `Iq` object with the same "id" as self, "from" and "to"
        attributes swapped, type="error" and containing <error /> element
        plus payload of `self`."""

        if self.get_type() not in ("set","get"):
            raise StanzaError,"Errors may only be generated for 'set' or 'get' iq"

        iq=Iq(typ="error",fr=self.get_to(),to=self.get_from(),
            sid=self.get_id(),error_cond=cond)
        n=self.get_query()
        if n:
            n=n.copyNode(1)
            iq.node.children.addPrevSibling(n)
        return iq

    def make_result_response(self):
        """Create result response for the a "get" or "set" iq stanza.

        :return: new `Iq` object with the same "id" as self, "from" and "to"
        attributes replaced and type="result"."""

        if self.get_type() not in ("set","get"):
            raise StanzaError,"Results may only be generated for 'set' or 'get' iq"

        iq=Iq(typ="result",fr=self.get_to(),to=self.get_from(),sid=self.get_id())
        return iq

    def new_query(self,ns_uri,name="query"):
        """Create new payload element for the stanza.

        :Parameters:
            - `ns_uri`: namespace URI of the element.
            - `name`: element name.
        
        :return: the new payload node."""
        return self.set_new_content(ns_uri,name)

    def get_query(self):
        """Get the payload element of the stanza.

        :return: the payload element or None if there is no payload."""
        for c in self.node.xpathEval("*"):
            try:
                if c.ns():
                    return c
            except libxml2.treeError:
                pass
        return None

    def get_query_ns(self):
        """Get a namespace of the stanza payload.

        :return: XML namespace URI of the payload or None if there is no payload."""
        q=self.get_query()
        if q:
            return get_node_ns_uri(q)
        else:
            return None

# vi: sts=4 et sw=4
