
import socket
import select
import random
import struct
import sys
import binascii
import time
import string
from types import StringType,UnicodeType,IntType

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

nameservers=[]
search_list=[]
cache={}

def load_resolv_conf():
	f=file("/etc/resolv.conf","r")
	nameservers[:]=[]
	search=[]
	domain=None
	for l in f.xreadlines():
		l=l.strip()
		if not l or l.startswith("#"):
			continue
		sp=l.split()
		if len(sp)<2:
			continue
		if sp[0]=="nameserver":
			nameservers.append(sp[1])
		elif sp[0]=="domain":
			domain=sp[1]
		elif sp[0]=="search":
			search=sp[1:]
	if search:
		search_list[:]=search
	elif domain:
		search_list[:]=[domain]
	else:
		search_list[:]=[]

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
			return domain_bin2str(packet,ptr,depth+1)[0],offset+2
		else:
			raise BadPacket
	return string.join(ret,"."),offset

def parse_a(packet,offset,len):
	if offset+4>len(packet):
		raise DataTruncated
	data=packet[offset:offset+4]
	data=[ord(b) for b in data] 
	return ("%i.%i.%i.%i" % tuple(data)),offset+4

def parse_cname(packet,offset,len):
	return domain_bin2str(packet,offset)

def parse_srv(packet,offset,len):
	if offset+7>len(packet):
		raise DataTruncated
	priority,weight,port=struct.unpack("!HHH",packet[offset:offset+6])
	target,offset=domain_bin2str(packet,offset+6)
	return (priority,weight,port,target),offset

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
	if not record_types.has_key(typ):
		return None,offset+rdl
	type_name,parse_func=record_types[typ]
	val,roffset=parse_func(packet,offset,len)
	if roffset!=offset+rdl:	
		raise BadPacket,"Record length mismatch"
	return (name,type_name,ttl,val),roffset

def parse_query(packet,offset):
	name,offset=domain_bin2str(packet,offset)
	if offset+4>len(packet):
		raise DataTruncated
	typ,cls=struct.unpack("!HH",packet[offset:offset+4])
	if cls!=1 or not record_types.has_key(typ):
		return None,offset+4
	return (name,record_types[typ][0],cls),offset+4
	
def make_query(name,typ):
	if type(typ)!=IntType:
		typ=query_types[typ]
	id=random.random()
	query=struct.pack("!HHHHHH",id,256,1,0,0,0) # query header (id, RD=1, 1 query)
	query+=domain_str2bin(name)
	query+=struct.pack("!HH",typ,1) # type, QCLASS=IN
	return query

def parse_result(packet):
	if len(packet)<12:
		raise DataTruncated
	id,flags,qdcount,ancount,nscount,arcount=struct.unpack("!HHHHHH",packet[:12])
	qr=flags&0x8000
	if not qr:
		raise BadPacket,"Received query instead of response"
	opcode=flags&0x7800>>11;
	aa=flags&0x4000;
	tc=flags&0x2000;
	ra=flags&0x80;
	rcode=flags&0x0f;
	if rcode:
		if resolve_errors.has_key(rcode):
			raise ResolverError,resolve_errors[rcode]
		else:
			raise ResolverError,"Unknown error %i" % (rcode,)

	question=[]
	answer=[]
	authority=[]
	additional=[]

	offset=12
	for i in range(0,qdcount):
		q,offset=parse_query(packet,offset)
		if q:
			question.append(q)
	try:
		for i in range(0,ancount):
			rr,offset=parse_rr(packet,offset)
			if rr:
				answer.append(rr)
		for i in range(0,nscount):
			rr,offset=parse_rr(packet,offset)
			if rr:
				authority.append(rr)
		for i in range(0,arcount):
			rr,offset=parse_rr(packet,offset)
			if rr:
				additional.append(rr)
	except DataTruncated:
		if not tc:
			raise	
	
	return answer,authority,additional

def query(name,typ):
	if "." in name or not search_list:
		return do_query(name,typ)
	else:
		e=None
		for d in search_list:
			try:
				r=do_query("%s.%s" % (name,d),typ)
				if r:
					return r
			except ResolverError,e:
				continue
		if e:
			raise e
				
	return None

def do_query(name,typ):
	if cache.has_key((name,typ)):
		print "key found in cache"
		ret=[]
		newvals=[]
		now=time.time()
		print "now:", now
		for exp,val in cache[name,typ]:
			if exp>now:
				ret.append(val)
				newvals.append((exp,val))
			else:
				print "expired: exp=%r val=%r" % (exp,val)
		if newvals:
			cache[name,typ]=newvals
		else:
			del cache[name,typ]
		print "cached: ",ret
		if ret:
			return ret
	if not nameservers:
		return None
	sockets=[]
	for ns in nameservers:
		for res in socket.getaddrinfo(ns,"domain",0,socket.SOCK_DGRAM):
			family,socktype,proto,canonname,sockaddr=res
			try:
				s=socket.socket(family,socktype,proto)
				s.connect(sockaddr)
			except socket.error, exc:
				if s:
					s.close()
				continue
			sockets.append(s)
	if not sockets:
		if exc:
			raise socket.error,exc
		else:
			return None

	result=None
	try:
		query=make_query(name,typ)
		print >>sys.stderr,"query: ",binascii.hexlify(query)
		result=query_ns(sockets,query)
	finally:
		for s in sockets:
			s.close()

	if not result:
		return None

	answer,authority,additional=result

	ret=[]
	for record in answer:
		rr_name,type_name,ttl,val=record
		ret.append(val)
		
	now=time.time()
	for record in answer+authority+additional:
		rr_name,type_name,ttl,val=record
		if cache.has_key((rr_name,type_name)):
			cache[rr_name,type_name].append((now+ttl,val))
		else:
			cache[rr_name,type_name]=[(now+ttl,val)]
		
	return ret


def query_ns(sockets,query):
	next_socket=0
	next_time=0
	interval=1
	retries=0
	while retries<3 and sockets:
		now=time.time()
		if now>next_time:
			if next_socket<len(sockets):
				s=sockets[next_socket]
				s.send(query)
				next_socket+=1
			if next_socket>=len(sockets):
				next_socket=0
				retries+=1
				interval*=2
			next_time=now+interval
		id,od,ed=select.select(sockets,[],[],0.5)
		for s in id:
			(res,addr)=s.recvfrom(1024)
			print >>sys.stderr,"result from %r: %s" % (addr,binascii.hexlify(res))
			if res[:2]==query[:2]:
				res=parse_result(res)
				if res:
					return res
	return None

query_types={
	"A": 1,
	"CNAME": 5,
	"SRV": 33,
	"*": 255,
	}

record_types={
	1: ("A",parse_a),
	5: ("CNAME",parse_cname),
	33: ("SRV",parse_srv),
	}

load_resolv_conf()

print query("jabber.bnet.pl","A")
print query("_jabber-server._tcp.jabber.bnet.pl","SRV")
print query("_jabber-server._tcp.jabber.bnet.pl","SRV")
print query("nic","A")
#resolve_srv("jabber-server","tcp","bnet.pl")
