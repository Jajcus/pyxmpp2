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

import time
from types import TupleType,IntType,FloatType

class ExpiringDictionary(dict):
    def __init__(self,default_timeout=300):
        self.timeouts={}
        self.default_timeout=default_timeout

    def __delitem__(self,key):
        del self.timeouts[key]
        return dict.__delitem__(self,key)

    def __setitem__(self,key,value):
        now=time.time()
        if type(key) is TupleType:
            if len(key)==2 and type(key[1]) in (IntType,FloatType):
                timeout=key[1]
                callback=None
            elif len(key)==2 and callable(key[1]):
                timeout=self.default_timeout
                callback=key[1]
            elif len(key)==3 and type(key[1]) in (IntType,FloatType) and callable(key[2]):
                timeout=key[1]
                callback=key[2]
            else:
                raise TypeError,"Key is a tuple, but invalid"
            self.timeouts[key[0]]=(now+timeout,callback)
            key=key[0]
        else:
            self.timeouts[key]=(now+self.default_timeout,None)
        return dict.__setitem__(self,key,value)

    def expire(self):
        now=time.time()
        for k,(timeout,callback) in self.timeouts.items():
            if timeout<=now:
                if callback:
                    callback(k,self[k])
                del self[k]
# vi: sts=4 et sw=4
