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

"""Utility functions for the pyxmpp package."""

__revision__="$Id: utils.py,v 1.16 2004/09/11 20:48:50 jajcus Exp $"
__docformat__="restructuredtext en"

import sys

if sys.hexversion<0x02030000:
    raise ImportError,"Python 2.3 or newer is required"

from types import UnicodeType,StringType
import re
import libxml2
import time
import datetime

def to_utf8(s):
    """
    Convevert `s` to UTF-8 if it is Unicode, leave unchanged
    if it is string or None and convert to string overwise
    """
    if s is None:
        return None
    elif type(s) is UnicodeType:
        return s.encode("utf-8")
    else:
        return str(s)

def from_utf8(s):
    """
    Convert `s` to Unicode or leave unchanged if it is None.

    Regular strings are assumed to be UTF-8 encoded
    """
    if s is None:
        return None
    elif type(s) is UnicodeType:
        return s
    elif type(s) is StringType:
        return unicode(s,"utf-8")
    else:
        return unicode(s)

evil_characters_re=re.compile(r"[\000-\010\013\014\016-\037]",re.UNICODE)
utf8_replacement_char=u"\ufffd".encode("utf-8")
def remove_evil_characters(s):
    """Remove control characters (not allowed in XML) from a string."""
    if type(s) is UnicodeType:
        return evil_characters_re.sub(u"\ufffd",s)
    else:
        return evil_characters_re.sub(utf8_replacement_char,s)

def get_node_ns(node):
    """Return namespace of the XML `node` or None if namespace is not set."""
    try:
        return node.ns()
    except libxml2.treeError:
        return None


def get_node_ns_uri(node):
    """Return namespace URI of the XML `node` or None if namespace is not set."""
    ns=get_node_ns(node)
    if ns:
        return ns.getContent()
    else:
        return None

minute=datetime.timedelta(minutes=1)
nulldelta=datetime.timedelta()

def datetime_utc_to_local(utc):
    """
    An ugly hack to convert naive `datetime.datetime` object containing
    UTC time to a naive `datetime.datetime` object with local time.
    It seems standard Python 2.3 library doesn't provide any better way to
    do that.
    """
    ts=time.time()
    cur=datetime.datetime.fromtimestamp(ts)
    cur_utc=datetime.datetime.utcfromtimestamp(ts)

    offset=cur-cur_utc
    t=utc

    d=datetime.timedelta(hours=2)
    while d>minute:
        local=t+offset
        tm=local.timetuple()
        tm=tm[0:8]+(0,)
        ts=time.mktime(tm)
        u=datetime.datetime.utcfromtimestamp(ts)
        diff=u-utc
        if diff<minute and diff>-minute:
                break
        if diff>nulldelta:
                offset-=d
        else:
                offset+=d
        d/=2
    return local

def datetime_local_to_utc(local):
        """
        Simple function to convert naive `datetime.datetime` object containing
        local time to a naive `datetime.datetime` object with UTC time.
        """
        ts=time.mktime(local.timetuple())
        return datetime.datetime.utcfromtimestamp(ts)

# vi: sts=4 et sw=4
