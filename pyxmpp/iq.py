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

import libxml2

from pyxmpp.utils import from_utf8,to_utf8,get_node_ns_uri
from pyxmpp.stanza import Stanza,StanzaError,gen_id

class Iq(Stanza):
    stanza_type="iq"
    def __init__(self,node=None,**kw):
        self.node=None
        if isinstance(node,Iq):
            pass
        elif isinstance(node,Stanza):
            raise TypeError,"Couldn't make Iq from other Stanza"
        elif isinstance(node,libxml2.xmlNode):
            pass
        elif node is not None:
            raise TypeError,"Couldn't make Iq from %r" % (type(node),)
        elif not kw.has_key("type"):
            raise StanzaError,"type is required for Iq"
        else:
            if not kw.has_key("id"):
                kw["id"]=gen_id()

        if kw.has_key("type") and kw["type"] not in ("get","set","result","error"):
            raise StanzaError,"Invalid Iq type: %r" % (type,)

        if node is None:
            node="iq"
        apply(Stanza.__init__,[self,node],kw)

    def copy(self):
        return Iq(self)

    def make_error_response(self,cond):
        if self.get_type() not in ("set","get"):
            raise StanzaError,"Errors may only be generated for 'set' or 'get' iq"

        iq=Iq(type="error",fr=self.get_to(),to=self.get_from(),
            id=self.get_id(),error_cond=cond)
        n=self.get_query()
        if n:
            n=n.copyNode(1)
            iq.node.children.addPrevSibling(n)
        return iq

    def make_result_response(self):
        if self.get_type() not in ("set","get"):
            raise StanzaError,"Results may only be generated for 'set' or 'get' iq"

        iq=Iq(type="result",fr=self.get_to(),to=self.get_from(),id=self.get_id())
        return iq

    def new_query(self,ns_uri,name="query"):
        return self.set_new_content(ns_uri,name)

    def get_query(self):
        for c in self.node.xpathEval("*"):
            try:
                if c.ns():
                    return c
            except libxml2.treeError:
                pass
        return None

    def get_query_ns(self):
        q=self.get_query()
        if q:
            return get_node_ns_uri(q)
        else:
            return None
# vi: sts=4 et sw=4
