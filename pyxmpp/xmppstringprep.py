
from types import ListType
import string
import stringprep
import unicodedata
import weakref

""" Stringprep (RFC3454) implementation with nodeprep and resourceprep profiles."""

class LookupFunction:
    def __init__(self,function):
        self.lookup=function

class LookupTable:
    def __init__(self,singles,ranges):
        self.singles=singles
        self.ranges=ranges
    def lookup(self,c):
        if self.singles.has_key(c):
            return self.singles[c]
        c=ord(c)
        for (min,max),value in self.ranges:
            if c<min:
                return None
            if c<=max:
                return value
        return None

A_1=LookupFunction(stringprep.in_table_a1)

def b1_mapping(uc):
    if stringprep.in_table_b1(uc):
        return u""
    else:
        return None

B_1=LookupFunction(b1_mapping)
B_2=LookupFunction(stringprep.map_table_b2)
B_3=LookupFunction(stringprep.map_table_b3)
C_1_1=LookupFunction(stringprep.in_table_c11)
C_1_2=LookupFunction(stringprep.in_table_c12)
C_2_1=LookupFunction(stringprep.in_table_c21)
C_2_2=LookupFunction(stringprep.in_table_c22)
C_3=LookupFunction(stringprep.in_table_c3)
C_4=LookupFunction(stringprep.in_table_c4)
C_5=LookupFunction(stringprep.in_table_c5)
C_6=LookupFunction(stringprep.in_table_c6)
C_7=LookupFunction(stringprep.in_table_c7)
C_8=LookupFunction(stringprep.in_table_c8)
C_9=LookupFunction(stringprep.in_table_c9)
D_1=LookupFunction(stringprep.in_table_d1)
D_2=LookupFunction(stringprep.in_table_d2)

def NFKC(input):
    if type(input) is ListType:
        input=string.join(input,u"")
    return unicodedata.normalize("NFKC",input)

class StringprepError(StandardError):
    """Exception raised when string preparation results in error."""
    pass

class Profile:
    """Base class for stringprep profiles."""
    cache_items=[]
    def __init__(self,unassigned,mapping,normalization,prohibited,bidi=1):
        """ Profile(unassigned,mapping,normalization,prohibited,bidi=1) -> Profile

        Constructor for a stringprep profile object.

        unassigned is a lookup table with unassigned codes
        mapping is a lookup table with character mappings
        normalization is a normalization function
        prohibited is a lookup table with prohibited characters
        bidi if 1 means bidirectional checks should be done
        """
        self.unassigned=unassigned
        self.mapping=mapping
        self.normalization=normalization
        self.prohibited=prohibited
        self.bidi=bidi
        self.cache={}

    def prepare(self,input):
        """Complete string preparation procedure for 'stored' strings.
        (includes checks for unassigned codes)"""
        r=self.cache.get(input)
        if r is not None:
            return r
        s=self.map(input)
        if self.normalization:
            s=self.normalization(s)
        s=self.prohibit(s)
        s=self.check_unassigned(s)
        if self.bidi:
            s=self.check_bidi(s)
        if type(s) is ListType:
            s=string.join(s)
        if len(self.cache_items)>=stringprep_cache_size:
            remove=self.cache_items[:-stringprep_cache_size/2]
            for profile,key in remove:
                try:
                    del profile.cache[key]
                except KeyError:
                    pass
            self.cache_items=self.cache_items[-stringprep_cache_size/2:]
        self.cache_items.append((self,input))
        self.cache[input]=s
        return s

    def prepare_query(self,s):
        """Complete string preparation procedure for 'query' strings.
        (without checks for unassigned codes)"""
        s=self.map(s)
        if self.normalization:
            s=self.normalization(s)
        s=self.prohibit(s)
        if self.bidi:
            s=self.check_bidi(s)
        if type(s) is ListType:
            s=string.join(s)
        return s

    def map(self,s):
        """Mapping part of string preparation."""
        r=[]
        for c in s:
            rc=None
            for t in self.mapping:
                rc=t.lookup(c)
                if rc is not None:
                    break
            if rc is not None:
                r.append(rc)
            else:
                r.append(c)
        return r

    def prohibit(self,s):
        """Checks for prohibited characters."""
        for c in s:
            for t in self.prohibited:
                if t.lookup(c):
                    raise StringprepError,"Prohibited character: %r" % (c,)
        return s

    def check_unassigned(self,s):
        """Checks for unassigned character codes."""
        for c in s:
            for t in self.unassigned:
                if t.lookup(c):
                    raise StringprepError,"Unassigned character: %r" % (c,)
        return s

    def check_bidi(self,s):
        """Checks if sting is valid for bidirectional printing."""
        has_L=0
        has_RAL=0
        for c in s:
            if D_1.lookup(c):
                has_RAL=1
            elif D_2.lookup(c):
                has_L=1
        if has_L and has_RAL:
            raise StringprepError,"Both RandALCat and LCat characters present"
        if has_RAL and (D_1.lookup(s[0]) is None or D_1.lookup(s[-1]) is None):
            raise StringprepError,"The first and the last character must be RandALCat"
        return s

nodeprep=Profile(
    unassigned=(A_1,),
    mapping=(B_1,B_2),
    normalization=NFKC,
    prohibited=(C_1_1,C_1_2,C_2_1,C_2_2,C_3,C_4,C_5,C_6,C_7,C_8,C_9,
            LookupTable({u'"':1,u'&':1,u"'":1,u"/":1,u":":1,u"<":1,u">":1,u"@":1},()) ),
    bidi=1)

resourceprep=Profile(
    unassigned=(A_1,),
    mapping=(B_1,),
    normalization=NFKC,
    prohibited=(C_1_2,C_2_1,C_2_2,C_3,C_4,C_5,C_6,C_7,C_8,C_9),
    bidi=1)

stringprep_cache_size=1000
def set_stringprep_cache_size(size):
    global stringprep_cache_size
    stringprep_cache_size=size
    if len(Profile.cache_items)>size:
        remove=Profile.cache_items[:-size]
        for profile,key in remove:
            try:
                del profile.cache[key]
            except KeyError:
                pass
        Profile.cache_items=Profile.cache_items[-size:]

# vi: sts=4 et sw=4
