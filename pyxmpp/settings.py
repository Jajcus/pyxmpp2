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
"""

from __future__ import absolute_import

__docformat__ = "restructuredtext en"

from collections import MutableMapping

class XMPPSettings(MutableMapping):
    """Container for various parameters used all over PyXMPP.
    
    It can be used like a regular dictionary, but will provide reasonable
    defaults for PyXMPP for parameters which are not explicitely set.
    
    :Classvariables:
        - `_defaults`: defaults for registered parameters.
        - `_defaults_factories`: factory functions providing default
                    values which cannot be hard-coded.
    :Instancevariables:
        - `_settings`: current values of the parameters explicitely set.
    """
    _defaults = {}
    _defaults_factories = {}
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

        :Raise: `KeyError` if parameter has no value and no global default

        :Return: parameter value
        """
        if key in self._settings:
            return self._settings[key]
        if local_default is not None:
            return local_default
        if key in self._defaults:
            return self._defaults[key]
        if key in self._defaults_factories:
            factory, call_once = self._defaults_factories[key]
            value = factory(self)
            if call_once:
                self._defaults[key] = value
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
    def add_defaults(cls, defaults):
        cls._defaults.update(defaults)
    @classmethod
    def add_default_factory(cls, setting, factory, cache = False):
        cls._defaults_factories[setting] = (factory, cache)

