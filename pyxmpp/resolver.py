
import socket
import select
import random
import struct
import sys
import binascii
import time
import string
from types import StringType,UnicodeType,IntType

import dns
from dns import ResolverError,DataTruncated,BadPacket,InvalidDomainName,resolve_errors

nameservers=[]
search_list=[]
cache={}

service_aliases={"xmpp-server": ("jabber-server","jabber")}

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
		ret=[]
		newvals=[]
		now=time.time()
		for exp,val in cache[name,typ]:
			if exp>now:
				ret.append(val)
				newvals.append((exp,val))
		if newvals:
			cache[name,typ]=newvals
		else:
			del cache[name,typ]
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
		query=dns.Message(None,0,rd=1,questions=[(name,typ,"IN")])
		result=query_ns(sockets,query)
	finally:
		for s in sockets:
			s.close()

	if not result:
		return None

	ret=[]
	for record in result.answers:
		ret.append(record)
		
	now=time.time()
	cache_update={}
	for rr in result.answers+result.authorities+result.additionals:
		if cache_update.has_key((rr.name,rr.type)):
			cache_update[rr.name,rr.type].append((now+rr.ttl,rr))
		else:
			cache_update[rr.name,rr.type]=[(now+rr.ttl,rr)]
	cache.update(cache_update)
		
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
				s.send(query.bin_format())
				next_socket+=1
			if next_socket>=len(sockets):
				next_socket=0
				retries+=1
				interval*=2
			next_time=now+interval
		id,od,ed=select.select(sockets,[],[],0.5)
		for s in id:
			(res,addr)=s.recvfrom(1024)
			res=dns.parse_message(res)
			if res.id==query.id:
				return res
	return None

def shuffle_srv(records):
	if not records:
		return []
	ret=[]
	while len(records)>1:
		sum=0
		for rr in records:
			sum+=rr.weight+0.1
		r=random.random()*sum
		sum=0
		for rr in records:
			sum+=rr.weight+0.1
			if r<sum:
				records.remove(rr)
				ret.append(rr)
				break
	ret.append(records[0])
	return ret

def reorder_srv(records):
	records=list(records)
	records.sort()
	ret=[]
	tmp=[]
	for rr in records:
		if not tmp or rr.priority==tmp[0].priority:
			tmp.append(rr)
			continue
		ret+=shuffle_srv(tmp)
	if tmp:
		ret+=shuffle_srv(tmp)
	return ret

def resolve_srv(domain,service,proto="tcp"):
	names_to_try=["_%s._%s.%s" % (service,proto,domain)]
	if service_aliases.has_key(service):
		for a in service_aliases[service]:
			names_to_try.append("_%s._%s.%s" % (a,proto,domain))
	for name in names_to_try:
		r=query(name,"SRV")
		if not r:
			continue
		if r and r[0].type=="CNAME":
			cname=r[0].target
			r=query(cname)
		return [(rr.target,rr.port) for rr in reorder_srv(r) if rr.type=="SRV"]
	return None

def getaddrinfo(host,port):
	ret=[]
	r=query(host,"A")
	if r and r[0].type=="CNAME":
		cname=r[0].target
		r=query(cname)
	else:
		cname=host
	for rr in r:
		if rr.type!="A":
			continue
		ret.append((socket.AF_INET,socket.SOCK_STREAM,
				socket.getprotobyname("tcp"),cname,(rr.ip,port)))
	return ret	

load_resolv_conf()

print "Resolving SRV for jabber.bnet.pl:"
ret=resolve_srv("jabber.bnet.pl","xmpp-server")
print "result:",ret

for i in range(10):
	print "Resolving SRV for nigdzie.:"
	ret=resolve_srv("nigdzie.","xmpp-server")
	for r in ret:
		print "Resolving address of",r[0]
		ai=getaddrinfo(r[0],r[1])
		print "The address is:",ai

#resolve_srv("jabber-server","tcp","bnet.pl")
