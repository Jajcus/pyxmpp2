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

""" Utility functions for pyxmpp package. """

from types import UnicodeType

def to_utf8(s):
	""" to_utf8(string_or_unicode) -> string

	If given unicode object returns is UTF-8 representation.
	If given string object returns it unchanged.
	If given object of any other type returns its string representation.
	When given None returns None."""
	if s is None:
		return None
	elif type(s) is UnicodeType:
		return s.encode("utf-8")
	else:
		return str(s)
	
def from_utf8(s):
	""" from_utf8(string_or_unicode) -> unicode

	If given unicode object returns it unchanged.
	If given string object converts it to unicode assuming UTF-8 encoding.
	If given object of any other type returns its unicode representation.
	When given None returns None."""
	if s is None:
		return None
	elif type(s) is UnicodeType:
		return s
	elif type(s) is StringType:
		return unicode(s,"utf-8")
	else:
		return unicode(s)
