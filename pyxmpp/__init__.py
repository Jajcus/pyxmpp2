#
# (C) Copyright 2003-2011 Jacek Konieczny <jajcus@jajcus.net>
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

"""
PyXMPP - Jabber/XMPP protocol implementation
============================================

Conventions
-----------

PyXMPP is object-oriented, most of its fetures are implemented via classes,
defined in various pyxmpp modules. The API is very asynchronous -- often
requested objects are not returned immediately, but instead a callback is
called when the object is available or an event occurs.

XMPPSettings objects
....................

As many parameters may define an XMPP implementation behaviour class
constructors or other methods would require lots of arguments to handle them
all. Instead, a special `XMPPSettings` object is often used, which can hold any
parameter usefull by any part of the PyXMPP.


Module hierarchy
................

Base XMPP features (`RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__, `RFC
3921 <http://www.ietf.org/rfc/rfc3921.txt>`__) are implemented in direct
submodules of `pyxmpp` package.
"""

__docformat__ = "restructuredtext en"

# vi: sts=4 et sw=4
