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

"""DNS resolever with SRV record support.

Normative reference:
  - `RFC 1035 <http://www.ietf.org/rfc/rfc1035.txt>`__
  - `RFC 2782 <http://www.ietf.org/rfc/rfc2782.txt>`__
"""

__revision__="$Id: resolver.py,v 1.18 2004/10/22 12:20:31 jajcus Exp $"
__docformat__="restructuredtext en"

import socket
import select
import random
import time
import re

from pyxmpp import dns
from pyxmpp.dns import DNSError

nameservers=[]
search_list=[]
cache={}

service_aliases={"xmpp-server": ("jabber-server","jabber")}

ip_re=re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

def load_resolv_conf():
    """Get the list of nameservers to use and domain to search from local configuration."""
    search=[]
    domain=None
    nameservers[:]=[]
    try:
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
    except IOError:
        pass

    if not nameservers:
        nameservers[:]=['127.0.0.1']
                
    if search:
        search_list[:]=search
    elif domain:
        search_list[:]=[domain]
    else:
        search_list[:]=[]

def query(name,rr_type):
    """Query the local cache and the configured nameservers for a DNS record using
    a search list if configured.

    :Parameters:
        - `name`: domain name to lookup.
        - `rr_type`: record type to lookup.
    :Types:
        - `name`: `unicode`
        - `rr_type`: `string`

    :raise DNSError: on error.

    :return: Records found.
    :returntype: `list` of `dns.RR`"""
    if search_list:
        e=None
        for d in search_list:
            try:
                r=do_query(u"%s.%s" % (name,d),rr_type)
                if r:
                    return r
            except DNSError,e:
                continue
        if e:
            raise e
    return do_query(name,rr_type)

def check_cache(name,rr_type):
    """Check the local cache for given DNS record.

    :Parameters:
        - `name`: domain name to lookup.
        - `rr_type`: record type to lookup.
    :Types:
        - `name`: `unicode`
        - `rr_type`: `string`

    :return: Records found or `None`.
    :returntype: `list` of `dns.RR`"""
    if not cache.has_key((name,rr_type)):
        return None
    ret=[]
    newvals=[]
    now=time.time()
    for exp,val in cache[name,rr_type]:
        if exp>now:
            ret.append(val)
            newvals.append((exp,val))
    if newvals:
        cache[name,rr_type]=newvals
    else:
        del cache[name,rr_type]
    return ret

def update_cache(records):
    """Update local cache with given records.

    :Parameters:
        - `records`: records to cache.
    :Types:
        - `records`: `dns.RR`"""
    now=time.time()
    cache_update={}
    for rr in records:
        if cache_update.has_key((rr.name,rr.type)):
            cache_update[rr.name,rr.type].append((now+rr.ttl,rr))
        else:
            cache_update[rr.name,rr.type]=[(now+rr.ttl,rr)]
    cache.update(cache_update)

def do_query(name,rr_type):
    """Query the local cache and the configured nameservers for a DNS record.

    :Parameters:
        - `name`: domain name to lookup.
        - `rr_type`: record type to lookup.
    :Types:
        - `name`: `unicode`
        - `rr_type`: `string`

    :raise DNSError: on error.

    :return: Records found.
    :returntype: `list` of `dns.RR`"""
    ret=check_cache(name,rr_type)
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
        query_msg=dns.Message(None,0,rd=1,questions=[(name,rr_type,"IN")])
        result=query_ns(sockets,query_msg)
    finally:
        for s in sockets:
            s.close()
    if not result:
        return None
    ret=[]
    for record in result.answers:
        ret.append(record)
    update_cache(result.answers+result.authorities+result.additionals)
    return ret

def query_ns(sockets,query_msg):
    """Send a DNS query to nameservers.

    :Parameters:
        - `sockets`: UDP sockets "connected" to nameservers.
        - `query_msg`: DNS query to send.
    :Types:
        - `sockets`: `list` of `socket.socket`
        - `query_msg`: `dns.Message`

    :return: result of the query or `None`.
    :returntype: `list` of `dns.RR`"""
    next_socket=0
    next_time=0
    interval=1
    retries=0
    while retries<3 and sockets:
        now=time.time()
        if now>next_time:
            if next_socket<len(sockets):
                s=sockets[next_socket]
                s.send(query_msg.bin_format())
                next_socket+=1
            if next_socket>=len(sockets):
                next_socket=0
                retries+=1
                interval*=2
            next_time=now+interval
        ifd=select.select(sockets,[],[],0.5)[0]
        for s in ifd:
            res=s.recv(1024)
            res=dns.parse_message(res)
            if res.id==query_msg.id:
                return res
    return None

def shuffle_srv(records):
    """Randomly reorder SRV records using their weights.

    :Parameters:
        - `records`: SRV records to shuffle.
    :Types:
        - `records`: `list` of `dns.RR_SRV`

    :return: reordered records.
    :returntype: `list` of `dns.RR_SRV`"""
    if not records:
        return []
    ret=[]
    while len(records)>1:
        weight_sum=0
        for rr in records:
            weight_sum+=rr.weight+0.1
        thres=random.random()*weight_sum
        weight_sum=0
        for rr in records:
            weight_sum+=rr.weight+0.1
            if thres<weight_sum:
                records.remove(rr)
                ret.append(rr)
                break
    ret.append(records[0])
    return ret

def reorder_srv(records):
    """Reorder SRV records using their priorities and weights.

    :Parameters:
        - `records`: SRV records to shuffle.
    :Types:
        - `records`: `list` of `dns.RR_SRV`

    :return: reordered records.
    :returntype: `list` of `dns.RR_SRV`"""
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
    """Resolve service domain to server name and port number using SRV records.

    A built-in service alias table will be used to lookup also some obsolete
    record names.

    :Parameters:
        - `domain`: domain name.
        - `service`: service name.
        - `proto`: protocol name.
    :Types:
        - `domain`: `unicode` or `str`
        - `service`: `unicode` or `str`
        - `proto`: `str`

    :return: host names and port numbers for the service or None.
    :returntype: `list` of (`str`,`int`)"""
    names_to_try=[u"_%s._%s.%s" % (service,proto,domain)]
    if service_aliases.has_key(service):
        for a in service_aliases[service]:
            names_to_try.append(u"_%s._%s.%s" % (a,proto,domain))
    for name in names_to_try:
        r=query(name,"SRV")
        if not r:
            continue
        if r and r[0].type=="CNAME":
            cname=r[0].target
            r=query(cname,"SRV")
        return [(rr.target,rr.port) for rr in reorder_srv(r) if rr.type=="SRV"]
    return None

def getaddrinfo(host,port,family=0,socktype=socket.SOCK_STREAM,proto=0):
    """Resolve host and port into addrinfo struct.

    Does the same thing as socket.getaddrinfo, but using `pyxmpp.resolver`. This
    makes it possible to reuse data (A records from the additional section of
    DNS reply) returned with SRV records lookup done using this module.

    :Parameters:
        - `host`: service domain name.
        - `port`: service port number or name.
        - `family`: address family.
        - `socktype`: socket type.
        - `proto`: protocol number or name.
    :Types:
        - `host`: `unicode` or `str`
        - `port`: `int` or `str`
        - `family`: `int`
        - `socktype`: `int`
        - `proto`: `int` or `str`

    :return: list of (family, socktype, proto, canonname, sockaddr).
    :returntype: `list` of (`int`, `int`, `int`, `str`, (`str`, `int`))"""
    ret=[]
    if proto==0:
        proto=socket.getprotobyname("tcp")
    elif type(proto)!=int:
        proto=socket.getprotobyname(proto)
    if type(port)!=int:
        port=socket.getservbyname(port,proto)
    if family not in (0,socket.AF_INET):
        raise NotImplementedError,"Protocol family other than AF_INET not supported, yet"
    if ip_re.match(host):
        return [(socket.AF_INET,socktype,proto,host,(host,port))]
    r=query(host,"A")
    if r and r[0].type=="CNAME":
        cname=r[0].target
        r=query(cname,"A")
    else:
        cname=host
    if r:
        for rr in r:
            if rr.type!="A":
                continue
            ret.append((socket.AF_INET,socktype,proto,cname,(rr.ip,port)))
    return ret

load_resolv_conf()

# vi: sts=4 et sw=4
