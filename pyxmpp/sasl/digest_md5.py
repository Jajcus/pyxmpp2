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

from binascii import b2a_hex as HEX, a2b_hex as unHEX
import re
import string
import md5
from types import UnicodeType
import sys

from core import ClientAuthenticator,ServerAuthenticator
from core import Reply,Failure,Response,Challenge,Success,Failure,PasswordManager

from pyxmpp.utils import to_utf8,from_utf8

def unquote(s):
	if s[0]!='"':
		return s
	return s[1:-1].replace('\\','')

def quote(s):
	s=s.replace('\\','\\\\')
	s=s.replace('"','\\"')
	return '%s' % (s,)

def H(s):
	return md5.new(s).digest()

def KD(k,s):
	return H("%s:%s" % (k,s))
	
def make_urp_hash(username,realm,passwd):
	if realm is None:
		realm=""
	if type(passwd) is UnicodeType:
		passwd=passwd.encode("utf-8")
	return H("%s:%s:%s" % (username,realm,passwd))

def compute_response(username,realm,urp_hash,nonce,cnonce,nonce_count,authzid,digest_uri):
	if authzid:
		A1="%s:%s:%s:%s" % (urp_hash,nonce,cnonce,authzid)
	else:
		A1="%s:%s:%s" % (urp_hash,nonce,cnonce)
	A2="AUTHENTICATE:"+digest_uri
	return HEX(KD( HEX(H(A1)),"%s:%s:%s:%s:%s" % (
			nonce,nonce_count,
			cnonce,"auth",HEX(H(A2)) ) ))

def compute_response_auth(username,realm,urp_hash,nonce,cnonce,nonce_count,authzid,digest_uri):
	if authzid:
		A1="%s:%s:%s:%s" % (urp_hash,nonce,cnonce,authzid)
	else:
		A1="%s:%s:%s" % (urp_hash,nonce,cnonce)
	A2=":"+digest_uri
	return HEX(KD( HEX(H(A1)),"%s:%s:%s:%s:%s" % (
			nonce,nonce_count,
			cnonce,"auth",HEX(H(A2)) ) ))

param_re=re.compile(r'^(?P<var>[^=]+)\=(?P<val>(\"(([^"\\]+)|(\\\")|(\\\\))+\")|([^",]+))(\,(?P<rest>.*))?$')

class DigestMD5ClientAuthenticator(ClientAuthenticator):
	def start(self,username,authzid,password=None):
		self.username=from_utf8(username)
		if authzid:
			self.authzid=from_utf8(authzid)
		else:
			self.authzid=""
		if password:
			self.password=from_utf8(password)
			self.pformat="plain"
		else:
			self.password=None
			self.pformat=None
		self.nonce_count=0
		self.response_auth=None
		self.rspauth_checked=0
		return Response()

	def challenge(self,challenge):
		if not challenge:
			self.debug("Empty challenge")
			return Failure("bad-challenge")

		if self.response_auth:
			return self.final_challenge(challenge)
	
		realms=[]
		nonce=None
		charset="iso-8859-1"
		realm=None
		while challenge:
			m=param_re.match(challenge)
			if not m:
				self.debug("Challenge syntax error: %r" % (challenge,))
				return Failure("bad-challenge")
			challenge=m.group("rest")
			var=m.group("var")
			val=m.group("val")
			self.debug("%r: %r" % (var,val))
			if var=="realm":
				realms.append(unquote(val))
			elif var=="nonce":
				if nonce:
					self.debug("Duplicate nonce")
					return Failure("bad-challenge")
				nonce=unquote(val)
			elif var=="qop":
				qopl=unquote(val).split(",")
				if "auth" not in qopl:
					self.debug("auth not supported")
					return Failure("not-implemented")
			elif var=="charset":
				if val!="utf-8":
					self.debug("charset given and not utf-8")
					return Failure("bad-challenge")
				charset="utf-8"
			elif var=="algorithm":
				if val!="md5-sess":
					self.debug("algorithm given and not md5-sess")
					return Failure("bad-challenge")

		if not nonce:
			self.debug("nonce not given")
			return Failure("bad-challenge")

		if self.password is None:
			self.password,self.pformat=self.password_manager.get_password(
						self.username,["plain","md5:user:realm:pass"])
		if not self.password or self.pformat not in ("plain","md5:user:realm:pass"):
			self.debug("Couldn't get plain password. Password: %r Format: %r"
							% (self.password,self.pformat))
			return Failure("password-unavailable")

		params=[]
		if realms:
			realms=[unicode(r,charset) for r in realms]
			realm=self.password_manager.choose_realm(realms)
		else:
			realm=self.password_manager.choose_realm([])
		if realm:
			if type(realm) is UnicodeType:
				try:
					realm=realm.encode(charset)
				except UnicodeError:
					self.debug("Couldn't encode realm to %r" % (charset,))
					return Failure("incompatible-charset")
			elif charset!="utf-8":
				try:
					realm=unicode(realm,"utf-8").encode(charser)
				except UnicodeError:
					self.debug("Couldn't encode realm from utf-8 to %r"
										% (charset,))
					return Failure("incompatible-charset")
			realm=quote(realm)
			params.append('realm="%s"' % (realm,))

		try:
			username=self.username.encode(charset)
		except UnicodeError:
			self.debug("Couldn't encode username to %r" % (charset,))
			return Failure("incompatible-charset")

		username=quote(username)
		params.append('username="%s"' % (username,))
			
		cnonce=self.password_manager.generate_nonce()
		cnonce=quote(cnonce)
		params.append('cnonce="%s"' % (cnonce,))
		
		params.append('nonce="%s"' % (quote(nonce),))

		self.nonce_count+=1
		nonce_count="%08x" % (self.nonce_count,)
		params.append('nc=%s' % (nonce_count,))
		
		params.append('qop=auth')
	
		serv_type=self.password_manager.get_serv_type().encode("us-ascii")
		host=self.password_manager.get_serv_host().encode("us-ascii")
		serv_name=self.password_manager.get_serv_name().encode("us-ascii")

		if serv_name:
			digest_uri="%s/%s/%s" % (serv_type,host,serv_name)
		else:
			digest_uri="%s/%s/%s" % (serv_type,host)
		
		digest_uri=quote(digest_uri)
		params.append('digest-uri="%s"' % (digest_uri,))

		if self.authzid:
			try:
				authzid=self.authzid.encode(charset)
			except UnicodeError:
				self.debug("Couldn't encode authzid to %r" % (charset,))
				return Failure("incompatible-charset")
			authzid=quote(authzid)
		else:
			authzid=""

		if self.pformat=="md5:user:realm:pass":
			urp_hash=self.password
		else:
			urp_hash=make_urp_hash(username,realm,self.password)
			
		response=compute_response(username,realm,urp_hash,nonce,cnonce,nonce_count,
							authzid,digest_uri)
		self.response_auth=compute_response_auth(username,realm,urp_hash,nonce,cnonce,
							nonce_count,authzid,digest_uri)

		params.append('response=%s' % (response,))

		if authzid:
			params.append('authzid="%s"' % (authzid,))
	
		return Response(string.join(params,","))

	def final_challenge(self,challenge):
		if self.rspauth_checked:
			return Failure("extra-challenge")
	
		rspauth=None
		while challenge:
			m=param_re.match(challenge)
			if not m:
				self.debug("Challenge syntax error: %r" % (challenge,))
				return Failure("bad-challenge")
			challenge=m.group("rest")
			var=m.group("var")
			val=m.group("val")
			self.debug("%r: %r" % (var,val))
			if var=="rspauth":
				rspauth=val
		
		if not rspauth:
			self.debug("Final challenge without rspauth")
			return Failure("bad-success")

		if rspauth==self.response_auth:
			self.rspauth_checked=1
			return Response("")
		else:
			self.debug("Wrong rspauth value - peer is cheating?")
			return Failure("bad-success")

	def finish(self,data):
		if self.rspauth_checked:
			return Success(self.authzid)
		else:
			self.final_challenge(data)

		if not self.response_auth:
			self.debug("Got success too early")
			return Failure("bad-success")

class DigestMD5ServerAuthenticator(ServerAuthenticator):
	def start(self,response):
		self.last_nonce_count=0
		params=[]
		realms=self.password_manager.get_realms()
		if realms:
			self.realm=quote(realms[0])
			for r in realms:
				r=quote(r)
				params.append('realm="%s"' % (r,))
		else:
			self.realm=None
		nonce=quote(self.password_manager.generate_nonce())
		self.nonce=nonce
		params.append('nonce="%s"' % (nonce,))
		params.append('qop="auth"')
		params.append('charset=utf-8')
		params.append('algorithm=md5-sess')
		self.authzid=None
		return Challenge(string.join(params,","))	
		
	def response(self,response):
		if self.authzid is not None:
			return Success(self.authzid)
	
		if not response:
			return Failure("not-authorized")
	
		if self.realm:
			realm=to_utf8(self.realm)
			realm=quote(realm)
		else:
			realm=None
		username=None
		cnonce=None
		digest_uri=None
		response_val=None
		authzid=None
		nonce_count=None
		while response:
			m=param_re.match(response)
			if not m:
				self.debug("Response syntax error: %r" % (response,))
				return Failure("not-authorized")
			response=m.group("rest")
			var=m.group("var")
			val=m.group("val")
			self.debug("%r: %r" % (var,val))
			if var=="realm":
				realm=val[1:-1]
			elif var=="cnonce":
				if cnonce:
					self.debug("Duplicate cnonce")
					return Failure("not-authorized")
				cnonce=val[1:-1]
			elif var=="qop":
				if val!='auth':
					self.debug("qop other then 'auth'")
					return Failure("not-authorized")
			elif var=="digest-uri":
				digest_uri=val[1:-1]
			elif var=="authzid":
				authzid=val[1:-1]
			elif var=="username":
				username=val[1:-1]
			elif var=="response":
				response_val=val
			elif var=="nc":
				nonce_count=val
				self.last_nonce_count+=1
				if int(nonce_count)!=self.last_nonce_count:
					self.debug("bad nonce: %r != %r" 
							% (nonce_count,self.last_nonce_count))
					return Failure("not-authorized")

		if not cnonce:
			self.debug("Required 'cnonce' parameter not given")
			return Failure("not-authorized")
		if not response_val:
			self.debug("Required 'response' parameter not given")
			return Failure("not-authorized")
		if not username:
			self.debug("Required 'username' parameter not given")
			return Failure("not-authorized")
		if not digest_uri:
			self.debug("Required 'digest_uri' parameter not given")
			return Failure("not-authorized")
		if not nonce_count:
			self.debug("Required 'nc' parameter not given")
			return Failure("not-authorized")

		username_uq=from_utf8(username.replace('\\',''))
		if authzid:
			authzid_uq=from_utf8(authzid.replace('\\',''))
		else:
			authzid_uq=None
		if realm:
			realm_uq=from_utf8(realm.replace('\\',''))
		else:
			realm_uq=None
		digest_uri_uq=digest_uri.replace('\\','')

		password,pformat=self.password_manager.get_password(
					username_uq,realm_uq,("plain","md5:user:realm:pass"))
		if pformat=="md5:user:realm:pass":
			urp_hash=password
		elif pformat=="plain":
			urp_hash=make_urp_hash(username,realm,password)
		else:
			self.debug("Couldn't get password.")
			return Failure("not-authorized")
			
		valid_response=compute_response(username,realm,urp_hash,self.nonce,cnonce,
							nonce_count,authzid,digest_uri)
		if response_val!=valid_response:
			self.debug("Response mismatch: %r != %r" % (response_val,valid_response))
			return Failure("not-authorized")

		s=digest_uri_uq.split("/")
		
		if len(s)==3:
			serv_type,host,serv_name=s
		elif len(s)==2:
			serv_type,host=s
			serv_name=None
		else:
			self.debug("Bad digest_uri: %r" % (digest_uri_uq,))
			return Failure("not-authorized")
	
		info={}
		info["mechanism"]="DIGEST-MD5"
		info["username"]=username_uq
		info["serv-type"]=serv_type
		info["host"]=host
		info["serv-name"]=serv_name
		if self.password_manager.check_authzid(authzid_uq,info):
			rspauth=compute_response_auth(username,realm,urp_hash,self.nonce,
							cnonce,nonce_count,authzid,digest_uri)
			self.authzid=authzid
			return Challenge("rspauth="+rspauth)
		else:
			self.debug("Authzid check failed")
			return Failure("invalid_authzid")
