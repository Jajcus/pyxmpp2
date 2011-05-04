#
# (C) Copyright 2003-2010 Jacek Konieczny <jajcus@jajcus.net>
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

__docformat__="restructuredtext en"

import re
import socket
from socket import AF_UNSPEC, AF_INET, AF_INET6
import dns.resolver
import dns.name
import dns.exception
import random
from encodings import idna

# check IPv6 support
try:
    socket.socket(AF_INET6)
except socket.error:
    default_address_family = AF_INET
else:
    default_address_family = AF_UNSPEC

def set_default_address_family(family):
    """Select default address family.

    :Parameters:
      - `family`: `AF_INET` for IPv4, `AF_INET6` for IPv6 and `AF_UNSPEC` for
        dual stack."""
    global default_address_family
    default_address_family = family

service_aliases={"xmpp-server": ("jabber-server","jabber")}

# should match all valid IP addresses, but can pass some false-positives,
# which are not valid domain names
ipv4_re=re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
ipv6_re=re.compile(r"^[0-9a-f]{0,4}:[0-9a-f:]{0,29}:([0-9a-f]{0,4}|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$")

def shuffle_srv(records):
    """Randomly reorder SRV records using their weights.

    :Parameters:
        - `records`: SRV records to shuffle.
    :Types:
        - `records`: sequence of `dns.rdtypes.IN.SRV`

    :return: reordered records.
    :returntype: `list` of `dns.rdtypes.IN.SRV`"""
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
        - `records`: `list` of `dns.rdtypes.IN.SRV`

    :return: reordered records.
    :returntype: `list` of `dns.rdtypes.IN.SRV`"""
    records=list(records)
    records.sort()
    ret=[]
    tmp=[]
    for rr in records:
        if not tmp or rr.priority==tmp[0].priority:
            tmp.append(rr)
            continue
        ret+=shuffle_srv(tmp)
        tmp = [rr]
    if tmp:
        ret+=shuffle_srv(tmp)
    return ret

def resolve_srv(domain, service, proto="tcp"):
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
        name=idna.ToASCII(name)
        try:
            r=dns.resolver.query(name, 'SRV')
        except dns.exception.DNSException:
            continue
        if not r:
            continue
        return [(rr.target.to_text(),rr.port) for rr in reorder_srv(r)]
    return None

def getaddrinfo(host, port, family = None,
                socktype = socket.SOCK_STREAM, proto = 0, allow_cname = True):
    """Resolve host and port into addrinfo struct.

    Does the same thing as socket.getaddrinfo, but using `dns.resolver`.

    :Parameters:
        - `host`: service domain name.
        - `port`: service port number or name.
        - `family`: address family (`AF_INET` for IPv4, `AF_INET6` for IPv6 or
          `AF_UNSPEC` for either, `None` for the auto-configured default).
        - `socktype`: socket type.
        - `proto`: protocol number or name.
        - `allow_cname`: when False CNAME responses are not allowed.
    :Types:
        - `host`: `unicode` or `str`
        - `port`: `int` or `str`
        - `family`: `int`
        - `socktype`: `int`
        - `proto`: `int` or `str`
        - `allow_cname`: `bool`

    :return: list of (family, socktype, proto, canonname, sockaddr).
    :returntype: `list` of (`int`, `int`, `int`, `str`, (`str`, `int`))"""
    if family is None:
        family = default_address_family
    ret=[]
    if proto==0:
        proto=socket.getprotobyname("tcp")
    elif type(proto)!=int:
        proto=socket.getprotobyname(proto)
    if type(port)!=int:
        port=socket.getservbyname(port,proto)
    if family not in (AF_UNSPEC, AF_INET, AF_INET6):
        raise NotImplementedError, "Unsupported protocol family."
    if ipv4_re.match(host) and family in (AF_UNSPEC, AF_INET):
        return [(AF_INET, socktype, proto, host, (host, port))]
    if ipv6_re.match(host) and family in (AF_UNSPEC, AF_INET6):
        return [(AF_INET6, socktype, proto, host, (host, port))]
    host=idna.ToASCII(host)
    rtypes = []
    if family in (AF_UNSPEC, AF_INET6):
        rtypes.append(("AAAA", AF_INET6))
    if family in (AF_UNSPEC, AF_INET):
        rtypes.append(("A", AF_INET))
    exception = None
    for rtype, rfamily in rtypes:
        try:
            try:
                r=dns.resolver.query(host, rtype)
            except dns.exception.DNSException:
                r=dns.resolver.query(host+".", rtype)
        except dns.exception.DNSException, err:
            exception = err
            continue
        if not allow_cname and r.rrset.name!=dns.name.from_text(host):
            raise ValueError,"Unexpected CNAME record found for %s" % (host,)
        if r:
            for rr in r:
                ret.append((rfamily, socktype, proto, r.rrset.name,
                                                        (rr.to_text(),port)))
    if not ret and exception:
        raise exception
    return ret

# vi: sts=4 et sw=4
