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
"""Jabber Service Discovery support.

Normative reference:
  - `JEP 30 <http://www.jabber.org/jeps/jep-0030.html>`__
"""

__revision__="$Id$"
__docformat__="restructuredtext en"

import libxml2

from pyxmpp.stanza import common_doc,common_root
from pyxmpp.jid import JID

from pyxmpp.utils import to_utf8

DISCO_NS="http://jabber.org/protocol/disco"
DISCO_ITEMS_NS=DISCO_NS+"#items"
DISCO_INFO_NS=DISCO_NS+"#info"

class DiscoError(StandardError):
    """Raised on disco related error"""
    pass

class DiscoItem:
    """An item of disco#items reply.

    :Ivariables:
        - `disco`: the disco reply this is the part of.
        - `xmlnode`: XML element describing the item.
    :Types:
        - `disco`: `DiscoItems`
        - `xmlnode`: `libxml2.xmlNode`
    """
    def __init__(self,disco,xmlnode_or_jid,node=None,name=None,action=None):
        """Initialize an `DiscoItem` object.

        :Parameters:
            - `disco`: the disco#items reply `self` is a part of.
            - `xmlnode_or_jid`: XML element describing the item or the JID of
              the item.
            - `node`: disco node of the item.
            - `name`: name of the item.
            - `action`: 'action' attribute of the item.
        :Types:
            - `disco`: `DiscoItems`
            - `xmlnode_or_jid`: `libxml2.xmlNode` or `JID`
            - `node`: `unicode`
            - `name`: `unicode`
            - `action`: `unicode`
        """
        self.disco=disco
        if isinstance(xmlnode_or_jid,JID):
            if disco:
                self.xmlnode=disco.xmlnode.newChild(disco.xmlnode.ns(),"item",None)
            else:
                self.xmlnode=common_root.newChild(None,"item",None)
                ns=self.xmlnode.newNs(DISCO_ITEMS_NS,None)
                self.xmlnode.setNs(ns)
            self.xmlnode.setProp("jid",xmlnode_or_jid.as_string())
        else:
            if disco is None:
                self.xmlnode=xmlnode_or_jid.copyNode(1)
            else:
                self.xmlnode=xmlnode_or_jid
        self.xpath_ctxt=common_doc.xpathNewContext()
        self.xpath_ctxt.setContextNode(self.xmlnode)
        self.xpath_ctxt.xpathRegisterNs("d",DISCO_ITEMS_NS)
        if name is not None:
            self.set_name(name)
        if node is not None:
            self.set_node(node)
        if action is not None:
            self.set_action(action)

    def __del__(self):
        if self.disco is None:
            if self.xmlnode:
                self.xmlnode.unlinkNode()
                self.xmlnode.freeNode()
                self.xmlnode=None
        if self.xpath_ctxt:
            self.xpath_ctxt.xpathFreeContext()
            
    def __str__(self):
        return self.xmlnode.serialize()

    def remove(self):
        """Remove `self` from the containing `DiscoItems` object."""
        if self.disco is None:
            return
        self.xmlnode.unlinkNode()
        oldns=self.xmlnode.ns()
        ns=self.xmlnode.newNs(oldns.getContent(),None)
        self.xmlnode.replaceNs(oldns,ns)
        common_root.addChild(self.xmlnode())
        self.disco=None

    def name(self):
        """Get the name of the item.

        :return: the name of the item or `None`.
        :returntype: `unicode`"""
        name=self.xmlnode.prop("name")
        if name is None:
            return None
        return unicode(name,"utf-8")

    def set_name(self,name):
        """Set the name of the item.

        :Parameters:
            - `name`: the new name or `None`.
        :Types:
            - `name`: `unicode` """
        if name is None:
            if self.xmlnode.hasProp("name"):
                self.xmlnode.unsetProp("name")
            return
        self.xmlnode.setProp("name",name.encode("utf-8"))

    def node(self):
        """Get the node of the item.

        :return: the node of the item or `None`.
        :returntype: `unicode`"""
        node=self.xmlnode.prop("node")
        if node is None:
            return None
        return unicode(node,"utf-8")

    def set_node(self,node):
        """Set the node of the item.

        :Parameters:
            - `node`: the new node or `None`.
        :Types:
            - `node`: `unicode`
        """
        if node is None:
            if self.xmlnode.hasProp("node"):
                self.xmlnode.unsetProp("node")
            return
        self.xmlnode.setProp("node",node.encode("utf-8"))

    def action(self):
        """Get the action attribute of the item.

        :return: the action of the item or `None`.
        :returntype: `unicode`"""
        action=self.xmlnode.prop("action")
        if action is None:
            return None
        return unicode(action,"utf-8")

    def set_action(self,action):
        """Set the action of the item.

        :Parameters:
            - `action`: the new action or `None`.
        :Types:
            - `action`: `unicode`
        """
        if action is None:
            if self.xmlnode.hasProp("action"):
                self.xmlnode.unsetProp("action")
            return
        if action not in ("remove","update"):
            raise DiscoError,"Action must be 'update' or 'remove'"
        self.xmlnode.setProp("action",action.encode("utf-8"))

    def jid(self):
        """Get the JID of the item.

        :return: the JID of the item.
        :returntype: `JID`"""
        return JID(self.xmlnode.prop("jid"))

    def set_jid(self,jid):
        """Set the JID of the item.

        :Parameters:
            - `jid`: the new jid.
        :Types:
            - `jid`: `JID`
        """
        self.xmlnode.setProp("jid",jid.as_unicode().encode("utf-8"))

class DiscoIdentity:
    """An <identity/> element of disco#info reply.

    Identifies an item by its name, category and type.

    :Ivariables:
        - `disco`: the disco reply this is the part of.
        - `xmlnode`: XML element describing the identity.
    :Types:
        - `disco`: `DiscoInfo`
        - `xmlnode`: `libxml2.xmlNode`
    """
    def __init__(self, disco, xmlnode_or_name, item_category=None, item_type=None, replace=False):
        """Initialize an `DiscoIdentity` object.

        :Parameters:
            - `disco`: the disco#info reply `self` is a part of.
            - `xmlnode_or_name`: XML element describing the identity or the
              name of the item described.
            - `item_category`: category of the item described.
            - `item_type`: type of the item described.
            - `replace`: if `True` than all other <identity/> elements in
              `disco` will be removed.
        :Types:
            - `disco`: `DiscoItems`
            - `xmlnode_or_name`: `libxml2.xmlNode` or `unicode`
            - `item_category`: `unicode`
            - `item_type`: `unicode`
            - `replace`: `bool`
        """
        self.disco=disco
        if disco and replace:
            old=disco.xpath_ctxt.xpathEval("d:identity")
            if old:
                for n in old:
                    n.unlinkNode()
                    n.freeNode()
        if isinstance(xmlnode_or_name,libxml2.xmlNode):
            if disco is None:
                self.xmlnode=xmlnode_or_name.copyNode(1)
            else:
                self.xmlnode=xmlnode_or_name
        elif not item_category:
            raise ValueError,"DiscoInfo requires category"
        else:
            if disco:
                self.xmlnode=disco.xmlnode.newChild(disco.xmlnode.ns(),"identity",None)
            else:
                self.xmlnode=common_root.newChild(None,"identity",None)
                ns=self.xmlnode.newNs(DISCO_INFO_NS,None)
                self.xmlnode.setNs(ns)
            self.xmlnode.setProp("name",to_utf8(xmlnode_or_name))
            self.xmlnode.setProp("category",to_utf8(item_category))
            if item_type:
                self.xmlnode.setProp("type",to_utf8(item_type))
        self.xpath_ctxt=common_doc.xpathNewContext()
        self.xpath_ctxt.setContextNode(self.xmlnode)
        self.xpath_ctxt.xpathRegisterNs("d",DISCO_INFO_NS)

    def __del__(self):
        if self.disco is None:
            if self.xmlnode:
                self.xmlnode.unlinkNode()
                self.xmlnode.freeNode()
                self.xmlnode=None
        if self.xpath_ctxt:
            self.xpath_ctxt.xpathFreeContext()
    def __str__(self):
        return self.xmlnode.serialize()

    def remove(self):
        """Remove `self` from the containing `DiscoInfo` object."""
        if self.disco is None:
            return
        self.xmlnode.unlinkNode()
        oldns=self.xmlnode.ns()
        ns=self.xmlnode.newNs(oldns.getContent(),None)
        self.xmlnode.replaceNs(oldns,ns)
        common_root.addChild(self.xmlnode())
        self.disco=None

    def name(self):
        """Get the name of the item.

        :return: the name of the item or `None`.
        :returntype: `unicode`"""
        var=self.xmlnode.prop("name")
        return unicode(var,"utf-8")

    def set_name(self,name):
        """Set the name of the item.

        :Parameters:
            - `name`: the new name or `None`.
        :Types:
            - `name`: `unicode` """
        if not name:
            raise ValueError,"name is required in DiscoIdentity"
        self.xmlnode.setProp("name",name.encode("utf-8"))

    def category(self):
        """Get the category of the item.

        :return: the category of the item.
        :returntype: `unicode`"""
        var=self.xmlnode.prop("category")
        return unicode(var,"utf-8")

    def set_category(self,category):
        """Set the category of the item.

        :Parameters:
            - `category`: the new category.
        :Types:
            - `category`: `unicode` """
        self.xmlnode.setProp("category",category.encode("utf-8"))

    def type(self):
        """Get the type of the item.

        :return: the type of the item.
        :returntype: `unicode`"""
        item_type=self.xmlnode.prop("type")
        if item_type is None:
            return None
        return unicode(item_type,"utf-8")

    def set_type(self,item_type):
        """Set the type of the item.

        :Parameters:
            - `item_type`: the new type.
        :Types:
            - `item_type`: `unicode` """
        if item_type is None:
            if self.xmlnode.hasProp("type"):
                self.xmlnode.unsetProp("type")
            return
        self.xmlnode.setProp("type",item_type.encode("utf-8"))

class DiscoItems:
    """A disco#items response or publish-request object.

    :Ivariables:
        - `xmlnode`: XML element listing the items.
    :Types:
        - `xmlnode`: `libxml2.xmlNode`
    """
    def __init__(self,xmlnode_or_node=None):
        """Initialize an `DiscoItems` object.
        
        Wrap an existing disco#items XML element or create a new one.

        :Parameters:
            - `xmlnode_or_node`: XML node to be wrapped into `self` or an item
              node name.
        :Types:
            - `xmlnode_or_node`: `libxml2.xmlNode` or `unicode`"""
        self.xmlnode=None
        self.xpath_ctxt=None
        if isinstance(xmlnode_or_node,libxml2.xmlNode):
            ns=xmlnode_or_node.ns()
            if ns.getContent() != DISCO_ITEMS_NS:
                raise DiscoError,"Bad disco-items namespace"
            self.xmlnode=xmlnode_or_node.docCopyNode(common_doc,1)
            common_root.addChild(self.xmlnode)
            self.ns=self.xmlnode.ns()
        else:
            self.xmlnode=common_root.newChild(None,"query",None)
            self.ns=self.xmlnode.newNs(DISCO_ITEMS_NS,None)
            self.xmlnode.setNs(self.ns)
            if xmlnode_or_node:
                self.xmlnode.setProp("node",to_utf8(xmlnode_or_node))
        self.xpath_ctxt=common_doc.xpathNewContext()
        self.xpath_ctxt.setContextNode(self.xmlnode)
        self.xpath_ctxt.xpathRegisterNs("d",DISCO_ITEMS_NS)

    def __del__(self):
        if self.xmlnode:
            self.xmlnode.unlinkNode()
            self.xmlnode.freeNode()
            self.xmlnode=None
        if self.xpath_ctxt:
            self.xpath_ctxt.xpathFreeContext()
            self.xpath_ctxt=None

    def node(self):
        """Get the node address of the `DiscoItems` object.

        :return: the node name.
        :returntype: `unicode`"""
        
        node=self.xmlnode.prop("node")
        if not node:
            return None
        return unicode(node,"utf-8")

    def items(self):
        """Get the items contained in `self`.

        :return: the items contained.
        :returntype: `list` of `DiscoItem`"""
        ret=[]
        l=self.xpath_ctxt.xpathEval("d:item")
        if l is not None:
            for i in l:
                ret.append(DiscoItem(self,i))
        return ret

    def add_item(self,jid,node=None,name=None,action=None):
        """Add a new item to the `DiscoItems` object.

        :Parameters:
            - `jid`: item JID.
            - `node`: item node name.
            - `name`: item name.
            - `action`: action for a "disco push".
        :Types:
            - `jid`: `pyxmpp.JID`
            - `node`: `unicode`
            - `name`: `unicode`
            - `actions`: `unicode`
            
        :returns: the item created.
        :returntype: `DiscoItem`."""
        return DiscoItem(self,jid,node,name,action)

    def has_item(self,jid,node=None):
        """Check if `self` contains an item.

        :Parameters:
            - `jid`: JID of the item.
            - `node`: node name of the item.
        :Types:
            - `jid`: `JID`
            - `node`: `libxml2.xmlNode`
            
        :return: `True` if the item is found in `self`.
        :returntype: `bool`"""
        #FIXME: stringprep!
        if not jid:
            raise ValueError,"bad jid"
        if isinstance(jid,JID):
            jid=jid.as_string()
        if not node:
            node_expr=""
        elif '"' not in node:
            expr=' and @node="%s"' % (node,)
        elif "'" not in node:
            expr=" and @node='%s'" % (node,)
        else:
            raise ValueError,"Invalid node name"
        if '"' not in jid:
            expr='d:item[@jid="%s"%s]' % (jid,node_expr)
        elif "'" not in jid:
            expr="d:item[@jid='%s'%s]" % (jid,node_expr)
        else:
            raise ValueError,"Invalid jid name"

        l=self.xpath_ctxt.xpathEval(expr)
        if l:
            return True
        else:
            return False

class DiscoInfo:
    """A disco#info response object.

    :Ivariables:
        - `xmlnode`: XML element listing the items.
    :Types:
        - `xmlnode`: `libxml2.xmlNode`
    """
    def __init__(self,xmlnode_or_node=None):
        """Initialize an `DiscoInfo` object.
        
        Wrap an existing disco#info XML element or create a new one.

        :Parameters:
            - `xmlnode_or_node`: XML node to be wrapped into `self` or an item
              node name.
        :Types:
            - `xmlnode_or_node`: `libxml2.xmlNode` or `unicode`"""
        self.xmlnode=None
        self.xpath_ctxt=None
        if isinstance(xmlnode_or_node,libxml2.xmlNode):
            ns=xmlnode_or_node.ns()
            if ns.getContent() != DISCO_INFO_NS:
                raise DiscoError,"Bad disco-info namespace"
            self.xmlnode=xmlnode_or_node.docCopyNode(common_doc,1)
            common_root.addChild(self.xmlnode)
            self.ns=self.xmlnode.ns()
        else:
            self.xmlnode=common_root.newChild(None,"query",None)
            self.ns=self.xmlnode.newNs(DISCO_INFO_NS,None)
            self.xmlnode.setNs(self.ns)
            if xmlnode_or_node:
                self.xmlnode.setProp("node",to_utf8(xmlnode_or_node))

        self.xpath_ctxt=common_doc.xpathNewContext()
        self.xpath_ctxt.setContextNode(self.xmlnode)
        self.xpath_ctxt.xpathRegisterNs("d",DISCO_INFO_NS)

    def __del__(self):
        if self.xmlnode:
            self.xmlnode.unlinkNode()
            self.xmlnode.freeNode()
            self.xmlnode=None
        if self.xpath_ctxt:
            self.xpath_ctxt.xpathFreeContext()
            self.xpath_ctxt=None

    def node(self):
        """Get the node address of the `DiscoInfo` object.

        :return: the node name.
        :returntype: `unicode`"""
        
        node=self.xmlnode.prop("node")
        if not node:
            return None
        return unicode(node,"utf-8")

    def features(self):
        """Get the features contained in `self`.

        :return: the list of features.
        :returntype: `list` of `unicode`"""
        l=self.xpath_ctxt.xpathEval("d:feature")
        ret=[]
        for f in l:
            if f.hasProp("var"):
                ret.append(unicode(f.prop("var"),"utf-8"))
        return ret

    def has_feature(self,var):
        """Check if `self` contains the named feature.

        :Parameters:
            - `var`: the feature name.
        :Types:
            - `var`: `unicode`
            
        :return: `True` if the feature is found in `self`.
        :returntype: `bool`"""
        if not var:
            raise ValueError,"var is None"
        if '"' not in var:
            expr='d:feature[@var="%s"]' % (var,)
        elif "'" not in var:
            expr="d:feature[@var='%s']" % (var,)
        else:
            raise DiscoError,"Invalid feature name"

        l=self.xpath_ctxt.xpathEval(expr)
        if l:
            return True
        else:
            return False

    def add_feature(self,var):
        """Add a feature to `self`.

        :Parameters:
            - `var`: the feature name.
        :Types:
            - `var`: `unicode`"""
        if self.has_feature(var):
            return
        n=self.xmlnode.newChild(self.ns,"feature",None)
        n.setProp("var",var)

    def remove_feature(self,var):
        """Remove a feature from `self`.

        :Parameters:
            - `var`: the feature name.
        :Types:
            - `var`: `unicode`"""
        if not var:
            raise ValueError,"var is None"
        if '"' not in var:
            expr='d:feature[@var="%s"]' % (var,)
        elif "'" not in var:
            expr="d:feature[@var='%s']" % (var,)
        else:
            raise DiscoError,"Invalid feature name"

        l=self.xpath_ctxt.xpathEval(expr)
        if not l:
            return

        for f in l:
            f.unlinkNode()
            f.freeNode()

    def identities(self):
        """List the identity objects contained in `self`.

        :return: the list of identities.
        :returntype: `list` of `DiscoIdentity`"""
        ret=[]
        l=self.xpath_ctxt.xpathEval("d:identity")
        if l is not None:
            for i in l:
                ret.append(DiscoIdentity(self,i))
        return ret

    def identity_is(self,item_category,item_type=None):
        """Check if the item described by `self` belongs to the given category 
        and type.
        
        :Parameters:
            - `item_category`: the category name.
            - `item_type`: the type name. If `None` then only the category is
              checked.
        :Types:
            - `item_category`: unicode
            - `item_type`: unicode
        
        :return: `True` if `self` contains at least one <identity/> object with
            given type and category.
        :returntype: `bool`"""
        if not item_category:
            raise ValueError,"bad category"
        if not item_type:
            type_expr=""
        elif '"' not in item_type:
            expr=' and @type="%s"' % (item_type,)
        elif "'" not in type:
            expr=" and @type='%s'" % (item_type,)
        else:
            raise ValueError,"Invalid type name"
        if '"' not in item_category:
            expr='d:feature[@category="%s"%s]' % (item_category,type_expr)
        elif "'" not in item_category:
            expr="d:feature[@category='%s'%s]" % (item_category,type_expr)
        else:
            raise ValueError,"Invalid category name"

        l=self.xpath_ctxt.xpathEval(expr)
        if l:
            return True
        else:
            return False

    def add_identity(self,item_name,item_category=None,item_type=None):
        """Add an identity to the `DiscoInfo` object.

        :Parameters:
            - `item_name`: name of the item.
            - `item_category`: category of the item.
            - `item_type`: type of the item.
        :Types:
            - `item_name`: `unicode`
            - `item_category`: `unicode`
            - `item_type`: `unicode`
            
        :returns: the identity created.
        :returntype: `DiscoIdentity`"""
        return DiscoIdentity(self,item_name,item_category,item_type)

# vi: sts=4 et sw=4
