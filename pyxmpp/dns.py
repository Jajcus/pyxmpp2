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

"""A simple implementation of a part of the DNS protocol."""

__revision__="$Id: dns.py,v 1.14 2004/09/20 21:07:19 jajcus Exp $"
__docformat__="restructuredtext en"

import random
import struct
from encodings import idna
from types import StringType,UnicodeType

class DNSError(Exception):
    """Base class for all DNS exception."""
    pass

class DataTruncated(DNSError):
    """Raised when part of data received is incomplete."""
    pass

class BadPacket(DNSError):
    """Raised when invalid DNS message is encountered."""
    pass

class InvalidDomainName(DNSError):
    """Raised when invalid domain name is used."""
    pass

resolve_errors={
    0: "OK",
    1: "Format error",
    2: "Server failure",
    3: "Name error",
    4: "Not implemented",
    5: "Refused",
    }

def domain_str2bin(name):
    """Convert domain name from a string to a binary representation.

    :param name: domain name.
    :type name: `unicode`

    :return: binary representation of the domain name.
    :returntype: `str`"""
    if type(name) is UnicodeType:
        name=idna.ToASCII(name)
    ret=""
    for label in name.split("."):
        if not label:
            continue
        if len(label)>63:
            raise InvalidDomainName
        ret+=chr(len(label))+label
    return ret+chr(0)

def domain_bin2str(packet,offset=0,depth=0):
    """Convert domain name from a binary representation in a message to a
    string. Recursively follow pointers in compressed domain names
    (uncompressing them them).

    :Parameters:
        - `packet`: data packed containing the encoded domain name.
        - `offset`: offset of the first byte of the encoded domain name.
        - `depth`: current recursion depth.
    :Types:
        - `packet`: `str`
        - `offset`: `int`
        - `depth`: `int`

    :return: decoded domain name.
    :returntype: `str`"""

    if depth>10:
        raise BadPacket,"Domain compression recursion limit reached"
    ret=[]
    while 1:
        if offset>len(packet):
            raise DataTruncated
        l=ord(packet[offset])
        if l==0:
            offset+=l+1
            break
        elif l<64:
            ret.append(packet[offset+1:offset+l+1])
            offset+=l+1
        elif l&0xc0==0xc0:
            l1=ord(packet[offset+1])
            ptr=((l&0x3f)<<8)+l1
            return ".".join(ret+[domain_bin2str(packet,ptr,depth+1)[0]]),offset+2
        else:
            raise BadPacket
    return ".".join(ret),offset

query_types_by_code={}
query_types_by_name={}
classes_by_name={ "IN": 1 }
classes_by_code={ 1: "IN" }

def _add_query_type(name,code):
    """Register a supported query type."""
    query_types_by_code[code]=name
    query_types_by_name[name]=code

class RR:
    """Base class for all DNS resource records types.

    :Cvariables:
        - `code`: code of the RR type.
        - `type`: name of the RR type.
        - `_rr_types_by_name`: mapping from RR type names to RR class.
        - `_rr_types_by_code`: mapping from RR type codes to RR class.

    :Ivariables:
        - `name`: domain name of the RR.
        - `ttl`: TTL value of the RR.
        - `cls`: class code or name of the RR.

    :Types:
        - `code`: `int`
        - `type`: `str`
        - `name`: `str`
        - `ttl`: `int`
        - `cls`: `int`
        - `_rr_types_by_name`: `dict`
        - `_rr_types_by_code`: `dict`
    """
    code=0
    type="?"
    _record_types_by_code={}
    _record_types_by_name={}
    def __init__(self,name,ttl,cls):
        """Initialize the RR object.

        :Parameters:
            - `name`: domain name of the RR.
            - `ttl`: TTL value of the RR.
            - `cls`: class code or name of the RR.
        :Types:
            - `name`: `str`
            - `ttl`: `int`
            - `cls`: `int`"""
        self.name=name
        self.ttl=ttl
        if type(cls) is StringType:
            self.cls=classes_by_name[cls]
        else:
            self.cls=cls

    def __str__(self):
        return "%20s %10i %s %s %s" % (self.name,self.ttl,classes_by_code[self.cls],
                self.type,self.format_data())

    def __repr__(self):
        return "<RR %s %s %s>" % (self.name,self.type,self.format_data())

    def __eq__(self,other):
        return (self.name==other.name
                and self.type==other.type
                and self.format_data()==other.format_data())

    def format_data(self):
        """Format RR data as a string.
        
        :return: formatted data.
        :returntype: `str`"""
        return ""

    def bin_format(self):
        """Create binary representation of the RR.

        :return: binary representation of the RR.
        :returntype: `str`"""
        if self.name is None or self.ttl is None:
            raise ValueError,"Incomplete RR"
        data=self.bin_format_data()
        if len(data)>65535:
            raise ValueError,"Data too long"
        return (domain_str2bin(self.name)+
                struct.pack("!HHIH",self.code,self.cls,self.ttl,len(data))+data)

    def bin_format_data(self):
        """Create binary representation of the RR data.

        :return: binary representation of the RR data.
        :returntype: `str`"""
        raise NotImplementedError

    def parse_bin(packet,offset):
        """Parse binary representation of the RR.

        :Parameters:
            - `packet`: the packet containing the RR.
            - `offset`: offset of the first byte of the RR data.
        :Types:
            - `packet`: `int`
            - `offset`: `int`

        :return: parsed RR and an offset of the next RR.
        :returntype: `RR`, `int`"""
        name,offset=domain_bin2str(packet,offset)
        if offset+10>len(packet):
            raise DataTruncated
        typ,cls,ttl,rdl=struct.unpack("!HHIH",packet[offset:offset+10])
        if offset+rdl>len(packet):
            raise DataTruncated
        offset+=10
        if cls!=1:
            return None,offset+rdl
        if not RR._record_types_by_code.has_key(typ):
            return None,offset+rdl
        rr_type=RR._record_types_by_code[typ]
        rr,roffset=rr_type.parse_bin_data(name,ttl,cls,packet,offset,len(packet))
        if roffset!=offset+rdl:
            raise BadPacket,"Record length mismatch"
        return rr,roffset
    
    parse_bin=staticmethod(parse_bin)

    def parse_bin_data(name,ttl,cls,packet,offset,length):
        """Parse binary representation of the RR data.

        :Parameters:
            - `name`: domain name of the RR.
            - `ttl`: TTL value of the RR.
            - `cls`: class code or name of the RR.
            - `packet`: the packet containing the RR.
            - `offset`: offset of the first byte of the RR data in the packet.
        :Types:
            - `name`: `str`
            - `ttl`: `int`
            - `cls`: `int`
            - `packet`: `int`
            - `offset`: `int`

        :return: parsed RR.
        :returntype: `RR`"""
        raise NotImplementedError

    parse_bin_data=staticmethod(parse_bin_data)

    def _add_record_type(py_class):
        """Register a supported record type."""
        _add_query_type(py_class.type,py_class.code)
        RR._record_types_by_code[py_class.code]=py_class
        RR._record_types_by_name[py_class.type]=py_class
    
    _add_record_type=staticmethod(_add_record_type)


class RR_A(RR):
    """'A' resource record.
    
    :Ivariables:
        - `ip`: the IP address contained in the record."""
    type="A"
    code=1
    def __init__(self,name,ttl,ip):
        """Initialize RR_A object.

        :Parameters:
            - `name`: domain name of the record.
            - `ttl`: TTL value of the record.
            - `ip`: IP address of the record."""
        RR.__init__(self,name,ttl,classes_by_name["IN"])
        self.ip=ip

    def format_data(self):
        """Format A RR data as a string.
        
        :return: formatted data.
        :returntype: `str`"""
        return self.ip

    def bin_format_data(self):
        """Create binary representation of the A RR data.

        :return: binary representation of the A RR data.
        :returntype: `str`"""
        ip1,ip2,ip3,ip4=self.ip.split(".")
        return struct.pack("!BBBB",int(ip1),int(ip2),int(ip3),int(ip4))

    def parse_bin_data(name,ttl,cls,packet,offset,length):
        """Parse binary representation of the A RR data.

        :Parameters:
            - `name`: domain name of the RR.
            - `ttl`: TTL value of the RR.
            - `cls`: class code or name of the RR.
            - `packet`: the packet containing the RR.
            - `offset`: offset of the first byte of the RR data in the packet.
        :Types:
            - `name`: `str`
            - `ttl`: `int`
            - `cls`: `int`
            - `packet`: `int`
            - `offset`: `int`

        :return: parsed RR.
        :returntype: `RR_A`"""
        if offset+4>len(packet):
            raise DataTruncated
        data=packet[offset:offset+4]
        data=[ord(b) for b in data]
        ip="%i.%i.%i.%i" % tuple(data)
        return RR_A(name,ttl,ip),offset+4
    
    parse_bin_data=staticmethod(parse_bin_data)

RR._add_record_type(RR_A)

class RR_NS(RR):
    """'NS' resource record.
    
    :Ivariables:
        - `target`: the nameserver name contained in the record."""
    type="NS"
    code=2
    def __init__(self,name,ttl,cls,target):
        """Initialize RR_NS object.

        :Parameters:
            - `name`: domain name of the record.
            - `ttl`: TTL value of the record.
            - `cls`: class name or code of the record.
            - `target`: the nameserver name contained in the record."""
        RR.__init__(self,name,ttl,cls)
        self.target=target

    def format_data(self):
        """Format NS RR data as a string.
        
        :return: formatted data.
        :returntype: `str`"""
        return self.target

    def bin_format_data(self):
        """Create binary representation of the NS RR data.

        :return: binary representation of the NS RR data.
        :returntype: `str`"""
        return domain_str2bin(self.target)

    def parse_bin_data(name,ttl,cls,packet,offset,length):
        """Parse binary representation of the NS RR data.

        :Parameters:
            - `name`: domain name of the RR.
            - `ttl`: TTL value of the RR.
            - `cls`: class code or name of the RR.
            - `packet`: the packet containing the RR.
            - `offset`: offset of the first byte of the RR data in the packet.
        :Types:
            - `name`: `str`
            - `ttl`: `int`
            - `cls`: `int`
            - `packet`: `int`
            - `offset`: `int`

        :return: parsed RR.
        :returntype: `RR_NS`"""
        target,offset=domain_bin2str(packet,offset)
        return RR_CNAME(name,ttl,cls,target),offset
        
    parse_bin_data=staticmethod(parse_bin_data)

RR._add_record_type(RR_NS)

class RR_CNAME(RR):
    """'CNAME' resource record.
    
    :Ivariables:
        - `target`: the name contained in the record."""
    type="CNAME"
    code=5
    def __init__(self,name,ttl,cls,target):
        """Initialize RR_CNAME object.

        :Parameters:
            - `name`: domain name of the record.
            - `ttl`: TTL value of the record.
            - `cls`: class name or code of the record.
            - `target`: the contained in the record."""
        RR.__init__(self,name,ttl,cls)
        self.target=target

    def format_data(self):
        """Format CNAME RR data as a string.
        
        :return: formatted data.
        :returntype: `str`"""
        return self.target

    def bin_format_data(self):
        """Create binary representation of the CNAME RR data.

        :return: binary representation of the CNAME RR data.
        :returntype: `str`"""
        return domain_str2bin(self.target)

    def parse_bin_data(name,ttl,cls,packet,offset,length):
        """Parse binary representation of the CNAME RR data.

        :Parameters:
            - `name`: domain name of the RR.
            - `ttl`: TTL value of the RR.
            - `cls`: class code or name of the RR.
            - `packet`: the packet containing the RR.
            - `offset`: offset of the first byte of the RR data in the packet.
        :Types:
            - `name`: `str`
            - `ttl`: `int`
            - `cls`: `int`
            - `packet`: `int`
            - `offset`: `int`

        :return: parsed RR.
        :returntype: `RR_CNAME`"""
        target,offset=domain_bin2str(packet,offset)
        return RR_CNAME(name,ttl,cls,target),offset
        
    parse_bin_data=staticmethod(parse_bin_data)

RR._add_record_type(RR_CNAME)

class RR_SOA(RR):
    """'SOA' resource record.
    
    :Ivariables:
        - `pri_master`: primary master nameserver for a zone.
        - `mailbox`: contact mailbox for a zone.
        - `serial`: serial number of a zone data.
        - `refresh`: refresh time for a zone.
        - `retry`: retry time for a zone.
        - `expire`: expire time for a zone.
        - `minimum`: minimum TTL time for a zone data."""
    type="SOA"
    code=6
    def __init__(self,name,ttl,cls,pri_master,mailbox,serial,refresh,retry,expire,minimum):
        """Initialize RR_SOA object.

        :Parameters:
            - `name`: domain name of the record.
            - `ttl`: TTL value of the record.
            - `cls`: class name or code of the record.
            - `pri_master`: primary master nameserver for a zone.
            - `mailbox`: contact mailbox for a zone.
            - `serial`: serial number of a zone data.
            - `refresh`: refresh time for a zone.
            - `retry`: retry time for a zone.
            - `expire`: expire time for a zone.
            - `minimum`: minimum TTL time for a zone data."""
        RR.__init__(self,name,ttl,cls)
        self.pri_master=pri_master
        self.mailbox=mailbox
        self.serial=serial
        self.refresh=refresh
        self.retry=retry
        self.expire=expire
        self.minimum=minimum

    def format_data(self):
        """Format SOA RR data as a string.
        
        :return: formatted data.
        :returntype: `str`"""
        return "%s %s %i %i %i %i %i" % (self.pri_master,self.mailbox,self.serial,
                self.refresh,self.retry,self.expire,self.minimum)

    def bin_format_data(self):
        """Create binary representation of the SOA RR data.

        :return: binary representation of the SOA RR data.
        :returntype: `str`"""
        return (domain_str2bin(self.pri_master)
                +domain_str2bin(self.mailbox)
                +struct.pack("!IIIII",self.serial,self.refresh,self.retry,
                self.expire,self.minimum))

    def parse_bin_data(name,ttl,cls,packet,offset,length):
        """Parse binary representation of the SOA RR data.

        :Parameters:
            - `name`: domain name of the RR.
            - `ttl`: TTL value of the RR.
            - `cls`: class code or name of the RR.
            - `packet`: the packet containing the RR.
            - `offset`: offset of the first byte of the RR data in the packet.
        :Types:
            - `name`: `str`
            - `ttl`: `int`
            - `cls`: `int`
            - `packet`: `int`
            - `offset`: `int`

        :return: parsed RR.
        :returntype: `RR_SOA`"""
        pri_master,offset=domain_bin2str(packet,offset)
        mailbox,offset=domain_bin2str(packet,offset)
        if offset+20>len(packet):
            raise DataTruncated
        serial,refresh,retry,expire,minimum=struct.unpack("!IIIII",packet[offset:offset+20])
        offset+=20
        return RR_SOA(name,ttl,cls,pri_master,mailbox,serial,refresh,retry,expire,minimum),offset
        
    parse_bin_data=staticmethod(parse_bin_data)

RR._add_record_type(RR_SOA)

class RR_SRV(RR):
    """'SRV' resource record.
    
    :Ivariables:
        - `priority`: priority value of the SRV record.
        - `weight`: weight value of the SRV record.
        - `port`: port number value of the SRV record.
        - `target`: server name value of the SRV record."""
    type="SRV"
    code=33
    def __init__(self,name,ttl,priority,weight,port,target):
        """Initialize RR_SOA object.

        :Parameters:
            - `name`: domain name of the record.
            - `ttl`: TTL value of the record.
            - `priority`: priority value of the SRV record.
            - `weight`: weight value of the SRV record.
            - `port`: port number value of the SRV record.
            - `target`: server name value of the SRV record."""
        RR.__init__(self,name,ttl,"IN")
        self.priority=priority
        self.weight=weight
        self.port=port
        self.target=target

    def format_data(self):
        """Format SRV RR data as a string.
        
        :return: formatted data.
        :returntype: `str`"""
        return "%i %i %i %s" % (self.priority,self.weight,self.port,self.target)

    def bin_format_data(self):
        """Create binary representation of the SRV RR data.

        :return: binary representation of the SRV RR data.
        :returntype: `str`"""
        return struct.pack("!HHH",self.priority,self.weight,self.port)+domain_str2bin(self.target)

    def __cmp__(self,other):
        return cmp(
                (self.name,self.target,self.port,self.priority,self.weight),
                (other.name,other.target,other.port,other.priority,other.weight)
            )

    def __eq__(self,other):
        return (self.name==other.name
                and self.target==other.target
                and self.port==other.port
                and self.weight==other.weight
                and self.priority==other.priority)

    def __gt__(self,other):
        return cmp(
                (self.name,self.target,self.port,self.priority,self.weight),
                (other.name,other.target,other.port,other.priority,other.weight)
            ) > 0

    def __le__(self,other):
        return not self.__gt__(other)

    def __lt__(self,other):
        return cmp(
                (self.name,self.target,self.port,self.priority,self.weight),
                (other.name,other.target,other.port,other.priority,other.weight)
            ) < 0

    def __ge__(self,other):
        return not self.__lt__(other)

    def parse_bin_data(name,ttl,cls,packet,offset,length):
        """Parse binary representation of the SRV RR data.

        :Parameters:
            - `name`: domain name of the RR.
            - `ttl`: TTL value of the RR.
            - `cls`: class code or name of the RR.
            - `packet`: the packet containing the RR.
            - `offset`: offset of the first byte of the RR data in the packet.
        :Types:
            - `name`: `str`
            - `ttl`: `int`
            - `cls`: `int`
            - `packet`: `int`
            - `offset`: `int`

        :return: parsed RR.
        :returntype: `RR_SRV`"""
        if offset+7>len(packet):
            raise DataTruncated
        priority,weight,port=struct.unpack("!HHH",packet[offset:offset+6])
        target,offset=domain_bin2str(packet,offset+6)
        return RR_SRV(name,ttl,priority,weight,port,target),offset
        
    parse_bin_data=staticmethod(parse_bin_data)

RR._add_record_type(RR_SRV)

_add_query_type("*",255)
_add_query_type("AXFR",252)


class Message:
    """DNS protocol message.
    
    :Ivariables:
        - `id`: a message id.
        - `qr`: query/response flag.
        - `opcode`: opcode value.
        - `aa`: authoritative answer flag.
        - `tc`: packet truncated flag.
        - `rd`: recursion desired flag.
        - `ra`: recursion available flag.
        - `rcode`: rcode value.
        - `questions`: the question section.
        - `answers`: the answer section.
        - `authorities`: the authority section.
        - `additionals`: the additional section.
    :Types:
        - `id`: `int`
        - `qr`: `bool`
        - `opcode`: `int`
        - `aa`: `bool`
        - `tc`: `bool`
        - `rd`: `bool`
        - `ra`: `bool`
        - `rcode`: `int`
        - `questions`: `list` of (name,qtype,class) tuples, where name is a domain name
          to query, qtype is an RR type or "*" or "AXFR" and class is class name
        - `answers`: `list` of `RR` objects
        - `authorities`: `list` of `RR` objects
        - `additionals`: `list` of `RR` objects"""
    def __init__(self,msg_id,qr,opcode=0,aa=False,tc=False,rd=False,ra=False,rcode=0,
            questions=None,answers=None,authorities=None,additionals=None):
        """Initialize the `Message` object.

        :Parameters:
            - `msg_id`: a message id.
            - `qr`: query/response flag.
            - `opcode`: opcode value.
            - `aa`: authoritative answer flag.
            - `tc`: packet truncated flag.
            - `rd`: recursion desired flag.
            - `ra`: recursion available flag.
            - `rcode`: rcode value.
            - `questions`: the question section.
            - `answers`: the answer section.
            - `authorities`: the authority section.
            - `additionals`: the additional section.
        :Types:
            - `msg_id`: `int`
            - `qr`: `bool`
            - `opcode`: `int`
            - `aa`: `bool`
            - `tc`: `bool`
            - `rd`: `bool`
            - `ra`: `bool`
            - `rcode`: `int`
            - `questions`: `list` of (name,qtype,class) tuples, where name is a domain name
              to query, qtype is an RR type or "*" or "AXFR" and class is class name
            - `answers`: `list` of `RR` objects
            - `authorities`: `list` of `RR` objects
            - `additionals`: `list` of `RR` objects"""
        if msg_id is None:
            self.id=random.randrange(0,65536)
        else:
            self.id=msg_id
        self.qr=qr
        self.opcode=opcode
        self.aa=aa
        self.tc=tc
        self.rd=rd
        self.ra=ra
        self.rcode=rcode
        if questions:
            self.questions=list(questions)
        else:
            self.questions=[]
        if answers:
            self.answers=list(answers)
        else:
            self.answers=[]
        if authorities:
            self.authorities=list(authorities)
        else:
            self.authorities=[]
        if additionals:
            self.additionals=list(additionals)
        else:
            self.additionals=[]

    def __str__(self):
        ret="DNS Message:"
        if self.qr:
            ret+=" response"
        else:
            ret+=" query"
        ret+=" opcode: "+`self.opcode`
        if self.aa:
            ret+=" AA"
        if self.tc:
            ret+=" TC"
        if self.rd:
            ret+=" RD"
        if self.ra:
            ret+=" RA"
        ret+=" rcode: "+`self.rcode`
        ret+="\n  Question section:\n"
        for name,qtype,cls in self.questions:
            ret+="    %20s %s %s\n" % (name,cls,qtype)
        if not self.qr:
            return ret
        ret+="  Answer section:\n"
        for rr in self.answers:
            ret+="    %s\n" % (rr,)
        ret+="  Authority section:\n"
        for rr in self.authorities:
            ret+="    %s\n" % (rr,)
        ret+="  Additional section:\n"
        for rr in self.additionals:
            ret+="    %s\n" % (rr,)
        return ret

    def is_query(self):
        """Check the message query/response flag.

        :return: `True` if the message is a query."""
        return not self.qr

    def is_response(self):
        """Check the message query/response flag.

        :return: `True` if the message is a response."""
        return self.qr

    def bin_format(self,maxsize=512):
        """Convert message to the "wire" format.

        :Parameters:
            - `maxsize`: the maximum size of the packet to be created.

        :return: The binary representaion of the message.
        :returntype: `str`"""
        payload=""
        qdcount=0
        for name,qtype,cls in self.questions:
            qtype=query_types_by_name[qtype]
            cls=classes_by_name[cls]
            data=domain_str2bin(name)+struct.pack("!HH",qtype,cls)
            if maxsize and len(data)+len(payload)+12>maxsize:
                self.tc=1
                break
            payload+=data
            qdcount+=1
        ancount=0
        for rr in self.answers:
            data=rr.bin_format()
            if maxsize and len(data)+len(payload)+12>maxsize:
                self.tc=1
                break
            payload+=data
            ancount+=1
        nscount=0
        for rr in self.authorities:
            data=rr.bin_format()
            if maxsize and len(data)+len(payload)+12>maxsize:
                self.tc=1
                break
            payload+=data
            nscount+=1
        arcount=0
        for rr in self.additionals:
            data=rr.bin_format()
            if maxsize and len(data)+len(payload)+12>maxsize:
                self.tc=1
                break
            payload+=data
            arcount+=1

        flags=0
        if self.qr:
            flags|=0x8000
        flags|=(self.opcode&0x0f)<<11
        if self.aa:
            flags|=0x0400
        if self.tc:
            flags|=0x0200
        if self.rd:
            flags|=0x0100
        if self.ra:
            flags|=0x0080
        flags|=(self.rcode&0x0f)
        return struct.pack("!HHHHHH",self.id,flags,qdcount,ancount,nscount,arcount)+payload

def parse_question(packet,offset):
    """Parse a question section field of a DNS message packet.

    :Parameters:
        - `packet`: the message packet.
        - `offset`: offset of the first byte of the field.
        
    :Types:
        - `packet`: `str`
        - `offset`: `int`

    :return: the question and the offset of the next field.
    :returntype: `tuple` of (name,qtype,class) tuple and `int`"""
    name,offset=domain_bin2str(packet,offset)
    if offset+4>len(packet):
        raise DataTruncated
    typ,cls=struct.unpack("!HH",packet[offset:offset+4])
    if cls!=1 or not query_types_by_code.has_key(typ):
        return None,offset+4
    return (name,query_types_by_code[typ],classes_by_code[cls]),offset+4

def parse_message(packet):
    """Parse a DNS message packet.

    :Parameters:
        - `packet`: the message packet.
        
    :return: new message object.
    :returntype: `Message`"""
    if len(packet)<12:
        raise DataTruncated
    msg_id,flags,qdcount,ancount,nscount,arcount=struct.unpack(
            "!HHHHHH",packet[:12])
    qr=(flags&0x8000)==0x8000
    opcode=flags&0x7800>>11;
    aa=(flags&0x0400)==0x0400;
    tc=(flags&0x0200)==0x0200;
    rd=(flags&0x0100)==0x0100;
    ra=(flags&0x0080)==0x0080;
    rcode=flags&0x0f;

    questions=[]
    answers=[]
    authorities=[]
    additionals=[]

    offset=12
    for i in range(0,qdcount):
        q,offset=parse_question(packet,offset)
        if q:
            questions.append(q)

    try:
        for i in range(0,ancount):
            rr,offset=RR.parse_bin(packet,offset)
            if rr:
                answers.append(rr)
        for i in range(0,nscount):
            rr,offset=RR.parse_bin(packet,offset)
            if rr:
                authorities.append(rr)
        for i in range(0,arcount):
            rr,offset=RR.parse_bin(packet,offset)
            if rr:
                additionals.append(rr)
    except DataTruncated:
        if not tc:
            raise

    return Message(msg_id,qr,opcode,aa,tc,rd,ra,rcode,
            questions,answers,authorities,additionals)

# vi: sts=4 et sw=4
