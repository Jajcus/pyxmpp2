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

"""jid --- Jabber ID handling"""

__revision__="$Id: jid.py,v 1.26 2004/09/10 13:18:32 jajcus Exp $"

import re
import weakref

from types import StringType,UnicodeType
from encodings import idna

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.xmppstringprep import nodeprep,resourceprep

node_invalid_re=re.compile(ur"[" u'"' ur"&'/:<>@\s\x00-\x19]",re.UNICODE)
resource_invalid_re=re.compile(ur"[\s\x00-\x19]",re.UNICODE)

def is_domain_valid(domain):
    try:
        idna.ToASCII(domain)
    except:
        return 0
    return 1
def are_domains_equal(a,b):
    a=idna.ToASCII(a)
    b=idna.ToASCII(b)
    return a.lower()==b.lower()

class JIDError(ValueError):
    "Exception raised when invalid JID is used"
    pass

class JID(object):
    cache=weakref.WeakValueDictionary()
    __slots__=["node","domain","resource","__weakref__"]
    def __new__(cls,node=None,domain=None,resource=None,check=1):
        """JID(string[,check=val]) -> JID
        JID(domain[,check=val]) -> JID
        JID(node,domain[,resource][,check=val]) -> JID

        Constructor for JID object.
        When check argument is given and equal 0, than JID
        is not checked for specification compliance. This
        should be used only when other arguments are known
        to be valid.

        JID objects are immutable
        """

        if isinstance(node,JID):
            return node

        if domain is None and resource is None:
            obj=cls.cache.get(node)
        else:
            obj=None
        if obj is None:
            obj=object.__new__(cls)

        if node and ((u"@" in node) or (u"/" in node)):
            obj.__from_string(node)
            cls.cache[node]=obj
        else:
            if domain is None and resource is None:
                if node is None:
                    raise JIDError,"At least domain must be given"
                domain=node
                node=None
            if check:
                obj.__set_node(node)
                obj.__set_domain(domain)
                obj.__set_resource(resource)
            else:
                object.__setattr__(obj,"node",node)
                object.__setattr__(obj,"domain",domain)
                object.__setattr__(obj,"resource",resource)
        return obj

    def __setattr__(self,name,value):
        raise RuntimeError,"JID objects are immutable!"

    def __from_string(self,s,check=1):
        return self.__from_unicode(from_utf8(s),check)

    def __from_unicode(self,s,check=1):
        s1=s.split(u"/",1)
        s2=s1[0].split(u"@",1)
        if len(s2)==2:
            if check:
                self.__set_node(s2[0])
                self.__set_domain(s2[1])
            else:
                object.__setattr__(self,"node",s2[0])
                object.__setattr__(self,"domain",s2[1])
        else:
            if check:
                self.__set_domain(s2[0])
            else:
                object.__setattr__(self,"domain",s2[0])
            object.__setattr__(self,"node",None)
        if len(s1)==2:
            if check:
                self.__set_resource(s1[1])
            else:
                object.__setattr__(self,"resource",s1[1])
        else:
            object.__setattr__(self,"resource",None)

    def __set_node(self,s):
        if s:
            s=from_utf8(s)
            s=nodeprep.prepare(s)
            if len(s)>1023:
                raise JIDError,"Node name too long"
        else:
            s=None
        object.__setattr__(self,"node",s)

    def __set_domain(self,s):
        if s: s=from_utf8(s)
        if s is None:
            raise JIDError,"Domain must be given"
        if not is_domain_valid(s):
            raise JIDError,"Invalid domain"
        if len(s)>1023:
            raise JIDError,"Domain name too long"
        object.__setattr__(self,"domain",s)

    def __set_resource(self,s):
        if s:
            s=from_utf8(s)
            s=resourceprep.prepare(s)
            if len(s)>1023:
                raise JIDError,"Resource name too long"
        else:
            s=None
        object.__setattr__(self,"resource",s)

    def __str__(self):
        return self.as_string()

    def __unicode__(self):
        return self.as_unicode()

    def __repr__(self):
        return "<JID: %r>" % (self.as_unicode())

    def as_utf8(self):
        "Returns UTF-8 encoded JID representation"
        return self.as_unicode().encode("utf-8")

    def as_string(self):
        "Returns UTF-8 encoded JID representation"
        return self.as_utf8()

    def as_unicode(self):
        "Unicode JID representation"
        r=self.domain
        if self.node:
            r=self.node+u'@'+r
        if self.resource:
            r=r+u'/'+self.resource
        if not JID.cache.has_key(r):
            JID.cache[r]=self
        return r

    def bare(self):
        "Returns bare JID made by removing resource from current JID"
        return JID(self.node,self.domain,check=0)

    def __eq__(self,other):
        if other is None:
            return 0
        elif type(other) in (StringType,UnicodeType):
            try:
                other=JID(other)
            except:
                return 0
        elif not isinstance(other,JID):
            raise TypeError,"Can't compare JID with %r" % (type(other),)

        return (self.node==other.node
            and are_domains_equal(self.domain,other.domain)
            and self.resource==other.resource)

    def __ne__(self,other):
        return not self.__eq__(other)

    def __cmp__(self,other):
        a=self.as_unicode()
        b=unicode(other)
        return cmp(a,b)

    def __hash__(self):
        return hash(self.node)^hash(self.domain)^hash(self.resource)

# vi: sts=4 et sw=4
