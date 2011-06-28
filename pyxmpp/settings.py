#
# (C) Copyright 2011 Jacek Konieczny <jajcus@jajcus.net>
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
# pylint: disable-msg=W0201

"""General settings container.

The behaviour of the XMPP implementation may be controlled by many, many
parameters, like addresses, authetication methods, TLS settings, keep alive, etc.
Those need to be passed from one component to other and passing it directly
via function parameters would only mess up the API.

Instead an `XMPPSettings` object will be used to pass all the optional
parameters. It will also provide the defaults.

This is also a mechanism for dependency injection, allowing different
components share the same objects, like event queue or DNS resolver
implementation.
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

from collections import MutableMapping, namedtuple

class _SettingDefinition(object):
    def __init__(self, name, type = unicode, default = None, factory = None,
                        cache = False, default_d = None, doc = None,
                        cmdline_help = None, validator = None, basic = False):
        self.name = name
        self.type = type
        self.default = default
        self.factory = factory
        self.cache = cache
        self.default_d = default_d
        self.doc = doc
        self.cmdline_help = cmdline_help
        self.basic = basic
        self.validator = None

class XMPPSettings(MutableMapping):
    """Container for various parameters used all over PyXMPP.
    
    It can be used like a regular dictionary, but will provide reasonable
    defaults for PyXMPP for parameters which are not explicitely set.

    All known PyXMPP settings are included in the :r:`settings list`.
    
    :CVariables:
        - `_defaults`: defaults for registered parameters.
        - `_defaults_factories`: factory functions providing default values
          which cannot be hard-coded.
    :Ivariables:
        - `_settings`: current values of the parameters explicitely set.
    """
    _defs = {}
    def __init__(self, data = None):
        """Create settings, optionally initialized with `data`.

        :Parameters:
            - `data`: initial data
        :Types:
            - `data`: any mapping, including `XMPPSettings`
        """
        if data is None:
            self._settings = {}
        else:
            self._settings = dict(data)
    def __len__(self):
        """Number of parameters set."""
        return len(self._settings)
    def __iter__(self):
        """Iterate over the parameter names."""
        for key in self._settings.iterkeys():
            return self[key]
    def __contains__(self, key):
        """Check if a parameter is set.
        
        :Parameters:
            - `key`: the parameter name
        :Types:
            - `key`: `unicode`
        """
        return key in self._settings
    def __getitem__(self, key):
        """Get a parameter value. Return the default if no value is set
        and the default is provided by PyXMPP.
        
        :Parameters:
            - `key`: the parameter name
        :Types:
            - `key`: `unicode`
        """
        return self.get(key, required = True)
    def __setitem__(self, key, value):
        """Set a parameter value.
        
        :Parameters:
            - `key`: the parameter name
            - `value`: the new value
        :Types:
            - `key`: `unicode`
        """
        self._settings[unicode(key)] = value
    def __delitem__(self, key):
        """Unset a parameter value.
        
        :Parameters:
            - `key`: the parameter name
        :Types:
            - `key`: `unicode`
        """
        del self._settings[key]
    def get(self, key, local_default = None, required = False):
        """Get a parameter value.
        
        If parameter is not set, return `local_default` if it is not `None`
        or the PyXMPP global default otherwise.

        :Raise `KeyError`: if parameter has no value and no global default

        :Return: parameter value
        """
        if key in self._settings:
            return self._settings[key]
        if local_default is not None:
            return local_default
        if key in self._defs:
            setting_def = self._defs[key]
            if setting_def.default is not None:
                return setting_def.default
            factory = setting_def.factory
            if factory is None:
                return None
            value = factory(self)
            if setting_def.cache is True:
                setting_def.default = value
            return value
        if required:
            raise KeyError(key)
        return local_default
    def keys(self):
        """Return names of parameters set.
        
        :Returntype: - `list` of `unicode`
        """
        return self._settings.keys()
    def items(self):
        """Return names and values of parameters set.
        
        :Returntype: - `list` of tuples
        """
        return self._settings.items()

    @classmethod
    def add_setting(cls, name, **kwargs):
        setting_def = _SettingDefinition(name, **kwargs)
        if name not in cls._defs:
            cls._defs[name] = setting_def
            return
        duplicate = cls._defs[name]
        if duplicate.type != setting_def.type:
            raise ValueError("Setting duplicate, with a different type")
        if duplicate.default != setting_def.default:
            raise ValueError("Setting duplicate, with a different default")
        if duplicate.factory != setting_def.factory:
            raise ValueError("Setting duplicate, with a different factory")

    @staticmethod
    def validate_string_list(value):
        try:
            return [x.strip() for x in value.split(u",")]
        except (AttributeError, TypeError):
            raise ValueError("Bad string list")
    
    @staticmethod
    def validate_positive_int(value):
        value = int(value)
        if value <= 0:
            raise ValueError("Positive number required")
        return value

    @staticmethod
    def validate_positive_float(value):
        value = float(value)
        if value <= 0:
            raise ValueError("Positive number required")
        return value

    @staticmethod
    def get_int_range_validator(start, stop):
        def validate_int_range(value):
            value = int(value)
            if value >= start and value < stop:
                return value
            raise ValueError("Not in <{0},{1}) range".format(start, stop))
        return validate_int_range
