
import random
import struct
import sys
import string
from types import StringType

class ResolverError(Exception):
	pass

class DataTruncated(ResolverError):
	pass

class BadPacket(ResolverError):
	pass

class InvalidDomainName(ResolverError):
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
	ret=""
	for label in name.split("."):
		if not label:
			continue
		if len(label)>63:
			raise InvalidDomainName
		ret+=chr(len(label))+label
	return ret+chr(0)

def domain_bin2str(packet,offset=0,depth=0):
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
			return string.join(ret+[domain_bin2str(packet,ptr,depth+1)[0]],"."),offset+2
		else:
			raise BadPacket
	return string.join(ret,"."),offset

query_types_by_code={}
query_types_by_name={}
record_types_by_code={}
record_types_by_name={}
record_bin_parsers={}
classes_by_name={ "IN": 1 }
classes_by_code={ 1: "IN" }

def add_query_type(name,code):
	query_types_by_code[code]=name
	query_types_by_name[name]=code

def add_record_type(cls,py_class,bin_parser):
	add_query_type(py_class.type,py_class.code)
	record_types_by_code[py_class.code]=py_class
	record_types_by_name[py_class.type]=py_class
	record_bin_parsers[py_class.code,cls]=bin_parser

class RR:
	code=0
	type="?"
	def __init__(self,name,ttl,cls):
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
		return ""

	def bin_format(self):
		if self.name is None or self.ttl is None:
			raise ValueError,"Incomplete RR"
		data=self.bin_format_data()
		if len(data)>65535:
			raise ValueError,"Data too long"
		return (domain_str2bin(self.name)+
				struct.pack("!HHIH",self.code,self.cls,self.ttl,len(data))+data)

	def bin_format_data(self):
		raise NotImplemented

class RR_A(RR):
	type="A"
	code=1
	def __init__(self,name,ttl,ip):
		RR.__init__(self,name,ttl,classes_by_name["IN"])
		self.ip=ip
	
	def format_data(self):
		return self.ip
		
	def bin_format_data(self):
		ip1,ip2,ip3,ip4=self.ip.split(".")
		return struct.pack("!BBBB",int(ip1),int(ip2),int(ip3),int(ip4))

def bin_parse_A(name,ttl,cls,packet,offset,len):
	if offset+4>len(packet):
		raise DataTruncated
	data=packet[offset:offset+4]
	data=[ord(b) for b in data] 
	ip="%i.%i.%i.%i" % tuple(data)
	return RR_A(name,ttl,ip),offset+4

add_record_type("IN",RR_A,bin_parse_A)

class RR_NS(RR):
	type="NS"
	code=2
	def __init__(self,name,ttl,cls,target):
		RR.__init__(self,name,ttl,cls)
		self.target=target
	
	def format_data(self):
		return self.target
		
	def bin_format_data(self):
		return domain_str2bin(self.target)

def bin_parse_NS(name,ttl,cls,packet,offset,len):
	target,offset=domain_bin2str(packet,offset)
	return RR_CNAME(name,ttl,cls,target),offset

add_record_type(None,RR_NS,bin_parse_NS)

class RR_CNAME(RR):
	type="CNAME"
	code=5
	def __init__(self,name,ttl,cls,target):
		RR.__init__(self,name,ttl,cls)
		self.target=target
	
	def format_data(self):
		return self.target
		
	def bin_format_data(self):
		return domain_str2bin(self.target)

def bin_parse_CNAME(name,ttl,cls,packet,offset,len):
	target,offset=domain_bin2str(packet,offset)
	return RR_CNAME(name,ttl,cls,target),offset

add_record_type(None,RR_CNAME,bin_parse_CNAME)

class RR_SOA(RR):
	type="SOA"
	code=6
	def __init__(self,name,ttl,cls,pri_master,mailbox,serial,refresh,retry,expire,minimum):
		RR.__init__(self,name,ttl,cls)
		self.pri_master=pri_master
		self.mailbox=mailbox
		self.serial=serial
		self.refresh=refresh
		self.retry=retry
		self.expire=expire
		self.minimum=minimum
	
	def format_data(self):
		return "%s %s %i %i %i %i %i" % (self.pri_master,self.mailbox,self.serial,
				self.refresh,self.retry,self.expire,self.minimum)
		
	def bin_format_data(self):
		return (domain_str2bin(self.pri_master)
				+domain_str2bin(self.mailbox)
				+struct.pack("!IIIII",self.serial,self.refresh,self.retry,
				self.expire,self.minimum))

def bin_parse_SOA(name,ttl,cls,packet,offset,len):
	pri_master,offset=domain_bin2str(packet,offset)
	mailbox,offset=domain_bin2str(packet,offset)
	if offset+20>len(packet):
		raise DataTruncated
	serial,refresh,retry,expire,minimum=struct.unpack("!IIIII",packet[offset:offset+20])
	offset+=20
	return RR_SOA(name,ttl,cls,pri_master,mailbox,serial,refresh,retry,expire,minimum),offset

add_record_type(None,RR_SOA,bin_parse_SOA)

class RR_SRV(RR):
	type="SRV"
	code=33
	def __init__(self,name,ttl,priority,weight,port,target):
		RR.__init__(self,name,ttl,"IN")
		self.priority=priority
		self.weight=weight
		self.port=port
		self.target=target
	
	def format_data(self):
		return "%i %i %i %s" % (self.priority,self.weight,self.port,self.target)
		
	def bin_format_data(self):
		return struct.pack("!HHH",self.priority,self.weight,self.port)+domain_str2bin(self.target)

	def __eq__(self,other):
		return (self.name==other.name
				and self.target==other.target
				and self.port==other.port
				and self.weight==other.weight
				and self.priority==other.priority)

	def __gt__(self,other):
		if self.name>other.name:
			return 1
		elif self.name<other.name:
			return 0
		if self.target>other.target:
			return 1
		elif self.target<other.target:
			return 0
		if self.port>other.port:
			return 1
		elif self.port<other.port:
			return 0
		if self.priority>other.priority:
			return 1
		elif self.priority<other.priority:
			return 0
		if self.weight>other.weight:
			return 1
		elif self.weight>other.weight:
			return 0
		return 0
	
	def __le__(self,other):
		return not self.__gt__(other)

	def __lt__(self,other):
		if self.name<other.name:
			return 1
		elif self.name>other.name:
			return 0
		if self.target<other.target:
			return 1
		elif self.target>other.target:
			return 0
		if self.port<other.port:
			return 1
		elif self.port>other.port:
			return 0
		if self.priority<other.priority:
			return 1
		elif self.priority>other.priority:
			return 0
		if self.weight>other.weight:
			return 1
		elif self.weight<other.weight:
			return 0
		return 0

	def __ge__(self,other):
		return not self.__lt__(other)

def bin_parse_SRV(name,ttl,cls,packet,offset,len):
	if offset+7>len(packet):
		raise DataTruncated
	priority,weight,port=struct.unpack("!HHH",packet[offset:offset+6])
	target,offset=domain_bin2str(packet,offset+6)
	return RR_SRV(name,ttl,priority,weight,port,target),offset

add_record_type("IN",RR_SRV,bin_parse_SRV)

add_query_type("*",255)
add_query_type("AXFR",252)

def parse_rr(packet,offset):
	name,offset=domain_bin2str(packet,offset)
	if offset+10>len(packet):
		raise DataTruncated
	typ,cls,ttl,rdl=struct.unpack("!HHIH",packet[offset:offset+10])
	if offset+rdl>len(packet):
		raise DataTruncated
	offset+=10
	if cls!=1:
		return None,offset+rdl
	if not record_types_by_code.has_key(typ):
		return None,offset+rdl
	cls_name=classes_by_code.get(cls)
	try:
		parse_func=record_bin_parsers[typ,cls_name]
	except KeyError:
		parse_func=record_bin_parsers[typ,None]
	rr,roffset=parse_func(name,ttl,cls,packet,offset,len)
	if roffset!=offset+rdl:	
		raise BadPacket,"Record length mismatch"
	return rr,roffset

class Message:
	def __init__(self,id,qr,opcode=0,aa=0,tc=0,rd=0,ra=0,rcode=0,
			questions=None,answers=None,authorities=None,additionals=None):
		if id is None:
			self.id=random.randrange(0,65536)
		else:
			self.id=id
		self.qr=qr
		self.opcode=opcode
		self.aa=aa
		self.tc=tc
		self.rd=rd
		self.ra=ra
		self.rcode=rcode
		if questions:
			self.questions=questions
		else:
			self.questions=[]
		if answers:
			self.answers=answers
		else:
			self.answers=[]
		if authorities:
			self.authorities=authorities
		else:
			self.authorities=[]
		if additionals:
			self.additionals=additionals
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
		for name,type,cls in self.questions:
			ret+="    %20s %s %s\n" % (name,cls,type)
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
		return not self.qr
		
	def is_response(self):
		return self.qr

	def bin_format(self,maxsize=512):
		payload=""
		qdcount=0
		for name,type,cls in self.questions:
			type=query_types_by_name[type]
			cls=classes_by_name[cls]
			data=domain_str2bin(name)+struct.pack("!HH",type,cls)
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
	name,offset=domain_bin2str(packet,offset)
	if offset+4>len(packet):
		raise DataTruncated
	typ,cls=struct.unpack("!HH",packet[offset:offset+4])
	if cls!=1 or not query_types_by_code.has_key(typ):
		return None,offset+4
	return (name,query_types_by_code[typ],classes_by_code[cls]),offset+4

def parse_message(packet):
	if len(packet)<12:
		raise DataTruncated
	id,flags,qdcount,ancount,nscount,arcount=struct.unpack("!HHHHHH",packet[:12])
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
			rr,offset=parse_rr(packet,offset)
			if rr:
				answers.append(rr)
		for i in range(0,nscount):
			rr,offset=parse_rr(packet,offset)
			if rr:
				authorities.append(rr)
		for i in range(0,arcount):
			rr,offset=parse_rr(packet,offset)
			if rr:
				additionals.append(rr)
	except DataTruncated:
		if not tc:
			raise	
	
	return Message(id,qr,opcode,aa,tc,rd,ra,rcode,questions,answers,authorities,additionals)

# vi: ts=4 sw=4
