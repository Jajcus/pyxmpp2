#
# (C) Copyright 2005 Jacek Konieczny <jajcus@jajcus.net>
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
"""Jabber Data Forms support.

Normative reference:
  - `JEP 4 <http://www.jabber.org/jeps/jep-0004.html>`__
"""

__revision__="$Id: disco.py 513 2005-01-09 16:34:00Z jajcus $"
__docformat__="restructuredtext en"

import sys
import libxml2
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.utils import from_utf8, to_utf8
from pyxmpp.jid import JID

class Option(StanzaPayloadObject):
    """One of optional data form field values.

    :Ivariables:
        - `label`: option label.
        - `value`: option value.
    :Types:
        - `label`: `unicode`
        - `value`: `unicode`
    """
    xml_element_name = "option"
    xml_element_namespace = "jabber:x:data"
    
    def __init__(self, value, label = None):
        """Initialize an `Option` object.

        :Parameters:
            - `value`: option value.
            - `label`: option label (human-readable description).
        :Types:
            - `label`: `unicode`
            - `value`: `unicode`
        """
	self.label = label
	self.value = value

    def complete_xml_element(self, xmlnode, doc):
        """Complete the XML node with `self` content.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `doc`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml.xmlNode`
            - `doc`: `libxml.xmlDoc"""
	xmlnode.setProp("label", self.label.encode("utf-8"))
	xmlnode.newTextChild(xmlnode.ns(), "value", self.value.encode("utf-8"))
	return xmlnode

    def _new_from_xml(cls, xmlnode):
        label = from_utf8(xmlnode.prop("label"))
        child = xmlnode.children
        while child:
            if (child.type != "element" or child.ns().content != "jabber:x:data"):
                pass
            elif child.name == "value":
                value = from_utf8(child.getContent())
            child = child.next
        return cls(value, label)
    _new_from_xml = classmethod(_new_from_xml)

class Field(StanzaPayloadObject):
    """A data form field.

    :Ivariables:
        - `name`: field name.
        - `values`: field values.
        - `value`: field value parsed according to the form type.
        - `label`: field label (human-readable description).
        - `type`: field type ("boolean", "fixed", "hidden", "jid-multi",
                "jid-single", "list-multi", "list-single", "text-multi", 
                "text-private" or "text-single").
        - `options`: field options (for "list-multi" or "list-single" fields).
        - `required`: `True` when the field is required.
        - `desc`: natural-language description of the field.
    :Types:
        - `name`: `unicode`
        - `values`: `list` of `unicode`
        - `value`: `unicode` or `list` or `pyxmpp.jid.JID` or `boolean`
        - `label`: `unicode`
        - `type`: `str`
        - `options`: `Option`
        - `required`: `boolean`
        - `desc`: `unicode`
    """ 
    xml_element_name = "field"
    xml_element_namespace = "jabber:x:data"
    allowed_types = ("boolean", "fixed", "hidden", "jid-multi",
                "jid-single", "list-multi", "list-single", "text-multi", 
                "text-private", "text-single")
    def __init__(self, name, values = None, field_type = None, label = None,
            options = None, required = False, desc = None):
	self.name = name 
        if field_type is not None and field_type not in self.allowed_types:
            raise ValueError, "Invalid form field type: %r" % (field_type,)
	self.type = field_type
        if not values:
            self.values = []
	else:
            self.values = list(values)
        if field_type and not field_type.endswith("-multi") and len(self.values) > 1:
            raise ValueError, "Multiple values for a single-value field"
	self.label = label
        if not options:
            self.options = []
        elif field_type and not field_type.startswith("list-"):
            raise ValueError, "Options not allowed for non-list fields"
        else:
            self.options = list(options)
        self.required = required
        self.desc = desc

    def __getattr__(self, name):
        if name != "value":
            raise AttributeError, "'Field' object has no attribute %r" % (name,)
        values = self.values
        t = self.type
        l = len(values)
        if t == "boolean":
            if l == 0:
                return None
            elif l == 1:
                v = values[0]
                if v == "0":
                    return False
                elif v == "1":
                    return True
            raise ValueError, "Bad boolean value"
        elif t.startswith("jid-"):
            values = [JID(v) for v in values]
        if t.endswith("-multi"):
            return values
        if l == 0:
            return None
        elif l == 1:
            return values[0]
        else:
            raise ValueError, "Multiple values of a single-value field"

    def __setattr__(self, name, value):
        if name != "value":
            self.__dict__[name] = value
            return
        t = self.type
        if t == "boolean":
            if value:
                self.values = ["1"]
            else:
                self.values = ["0"]
            return
        if t.endswith("-multi"):
            values = list(value)
        else:
            values = [value]
        if t.startswith("jid-"):
            values = [JID(v).as_unicode() for v in values]
        self.values = values

    def add_option(self, value, label):
        """Add an option for the field.

        :Parameters:
            - `label`: option label (human-readable description).
            - `value`: option value.
        :Types:
            - `label`: `unicode`
            - `value`: `unicodez
        """
	option = Option(value, label)
	self.options.append(option)
	return option

    def complete_xml_element(self, xmlnode, doc):
        """Complete the XML node with `self` content.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `doc`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml.xmlNode`
            - `doc`: `libxml.xmlDoc"""
        if self.type is not None and self.type not in self.allowed_types:
            raise ValueError, "Invalid form field type: %r" % (field_type,)
	xmlnode.setProp("type", self.type)
	if not self.label is None:
	    xmlnode.setProp("label", self.label)
	if not self.name is None:
	    xmlnode.setProp("var", self.name)
	if self.values:
            if self.type and len(self.values) > 1 and not self.type.endswith(u"-multi"):
                raise ValueError, "Multiple values not allowed for %r field" % (self.type,)
            for value in self.values:
                xmlnode.newTextChild(xmlnode.ns(), "value", to_utf8(value))
	for option in self.options:
	    option.as_xml(xmlnode, doc)
        if self.required:
            xmlnode.newChild(xmlnode.ns(), "required", None)
        if self.desc:
            xmlnode.newTextChild(xmlnode.ns(), "desc", to_utf8(self.desc))
	return xmlnode

    def _new_from_xml(cls, xmlnode):
        field_type = xmlnode.prop("type")
        label = from_utf8(xmlnode.prop("label"))
        name = from_utf8(xmlnode.prop("var"))
        child = xmlnode.children
        values = []
        options = []
        required = False
        desc = None
        while child:
            if child.type != "element" or child.ns().content != "jabber:x:data":
                pass
            elif child.name == "required":
                required = True
            elif child.name == "desc":
                desc = from_utf8(child.getContent())
            elif child.name == "value":
                values.append(from_utf8(child.getContent()))
            elif child.name == "option":
                options.append(Option._new_from_xml(child))
            child = child.next
        if field_type and not field_type.endswith("-multi") and len(values) > 1:
            raise ValueError, "Multiple values for a single-value field"
        return cls(name, values, field_type, label, options, required, desc)
    _new_from_xml = classmethod(_new_from_xml)

class Item(StanzaPayloadObject):
    xml_element_name = "item"
    xml_element_namespace = "jabber:x:data"
    def __init__(self, fields):
	self.fields = list(fields)

    def __getitem__(self, name_or_index):
        if isinstance(name_or_index, int):
            return self.fields[name_or_index]
        for f in self.fields:
            if f.name == name_or_index:
                return f
        raise KeyError, name_or_index
     
    def __contains__(self, name):
        for f in self.fields:
            if f.name == name:
                return True
        return False

    def __iter__(self):
        for field in self.fields:
            yield field

    def add_field(self, name = None, values = None, field_type = None, label = None, options = None):
	field = Field(name, values, field_type, label, options)
	self.fields.append(field)
	return field

    def complete_xml_element(self, xmlnode, doc):
        """Complete the XML node with `self` content.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `doc`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml.xmlNode`
            - `doc`: `libxml.xmlDoc"""
	for field in self.fields:
	    field.as_xml(xmlnode, doc)
    def _new_from_xml(cls, xmlnode):
        child = xmlnode.children
        fields = []
        while child:
            if child.type != "element" or child.ns().content != "jabber:x:data":
                pass
	    elif child.name == "field":
                fields.append(Field._new_from_xml(child))
	    child = child.next
        return cls(fields)
    _new_from_xml = classmethod(_new_from_xml)

class Form(StanzaPayloadObject):
    allowed_types = ("form", "submit", "cancel", "result")
    xml_element_name = "x"
    xml_element_namespace = "jabber:x:data"
    def __init__(self, xmlnode_or_type = "form", title = None, instructions = None,
            fields = None, reported_fields = None, items = None):
        if isinstance(xmlnode_or_type, libxml2.xmlNode):
            self.__from_xml(xmlnode_or_type)
        elif xmlnode_or_type not in self.allowed_types:
            raise ValueError, "Form type %r not allowed." % (xmlnode_or_type,)
        else:
            self.type = xmlnode_or_type
            self.title = title
            self.instructions = instructions
            if fields:
                self.fields = list(fields)
            else:
                self.fields = []
            if reported_fields:
                self.reported_fields = list(reported_fields)
            else:
                self.reported_fields = []
            if items:
                self.items = list(items)
            else:
                self.items = []

    def __getitem__(self, name_or_index):
        if isinstance(name_or_index, int):
            return self.fields[name_or_index]
        for f in self.fields:
            if f.name == name_or_index:
                return f
        raise KeyError, name_or_index

    def __contains__(self, name):
        for f in fields:
            if f.name == name:
                return True
        return False

    def __iter__(self):
        for field in self.fields:
            yield field

    def add_field(self, name = None, values = None, field_type = None, label = None, options = None, required = False, desc = None):
	field = Field(name, values, field_type, label, options, required, desc)
	self.fields.append(field)
	return field

    def add_item(self, fields):
        item = Item(fields)
        self.items.append(item)
        return item

    def complete_xml_element(self, xmlnode, doc):
        """Complete the XML node with `self` content.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `doc`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml.xmlNode`
            - `doc`: `libxml.xmlDoc"""
        if self.type not in self.allowed_types:
            raise ValueError, "Form type %r not allowed." % (self.type,)
        xmlnode.setProp("type", self.type)
        if self.type == "cancel":
            return
        ns = xmlnode.ns()
	if self.title is not None:
	    xmlnode.newTextChild(ns, "title", self.title)
	if self.instructions is not None:
	    xmlnode.newTextChild(ns, "instructions", self.instructions)
	for field in self.fields:
	    field.as_xml(xmlnode, doc)
        if self.type != "result":
            return
        if self.reported_fields:
	    Textreported = node.newChild(ns, "reported", None)
            for field in self.reported_fields:
                field.as_xml(reported, doc)
	for items in self.items:
	    item.as_xml(xmlnode, doc)

    def __from_xml(self, xmlnode):
        self.fields = []
        self.reported_fields = []
        self.items = []
        self.title = None
        self.instructions = None
        if (xmlnode.type != "element" or xmlnode.name != "x" 
                or xmlnode.ns().content != "jabber:x:data"):
            raise ValueError, "Not a form: %r" % (xmlnode.serialize(),)
        self.type = xmlnode.prop("type")
        if not self.type in self.allowed_types:
            raise ValueError, "Bad form type: %r" % (self.type,)
        child = xmlnode.children
        while child:
            if child.type != "element" or child.ns().content != "jabber:x:data":
                pass
	    elif child.name == "title":
                self.title = from_utf8(child.getContent())
	    elif child.name == "instructions":
                self.instructions = from_utf8(child.getContent())
	    elif child.name == "field":
                self.fields.append(Field._new_from_xml(child))
            elif child.name == "item":
                self.items.append(Item._new_from_xml(child))
            elif child.name == "reported":
                self.__get_reported(child)
	    child = child.next

    def __get_reported(self, xmlnode):
        child = xmlnode.children
        while child:
            if child.type != "element" or child.ns().content != "jabber:x:data":
                pass
	    elif child.name == "field":
                self.reported_fields.append(Field._new_from_xml(child))
	    child = child.next
