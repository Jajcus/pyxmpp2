from binascii import b2a_hex as HEX, a2b_hex as unHEX
import re
import string
import md5
from types import UnicodeType
import sys

from core import ClientAuthenticator,ServerAuthenticator
from core import Reply,Abort,Response,Challenge,Success,Failure,PasswordManager

from utils import to_utf8,from_utf8

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
	print >>sys.stderr,"Response of:",`(username,realm,urp_hash,nonce,cnonce,nonce_count,authzid,digest_uri)`
	if authzid:
		A1="%s:%s:%s:%s" % (urp_hash,nonce,cnonce,authzid)
	else:
		A1="%s:%s:%s" % (urp_hash,nonce,cnonce)
	A2="AUTHENTICATE:"+digest_uri
	return HEX(KD( HEX(H(A1)),"%s:%s:%s:%s:%s" % (
			nonce,nonce_count,
			cnonce,"auth",HEX(H(A2)) ) ))

def compute_response_auth(username,realm,urp_hash,nonce,cnonce,nonce_count,authzid,digest_uri):
	print >>sys.stderr,"Response auth of:",`(username,realm,urp_hash,nonce,cnonce,nonce_count,authzid,digest_uri)`
	if authzid:
		A1="%s:%s:%s:%s" % (urp_hash,nonce,cnonce,authzid)
	else:
		A1="%s:%s:%s" % (urp_hash,nonce,cnonce)
	A2=":"+digest_uri
	nonce_count="%08x" % (nonce_count,)
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
			self.authzid=None
		self.nonce_count=0
		return Response()

	def challenge(self,challenge):
		if not challenge:
			self.debug("Empty challenge")
			return Abort("bad-challenge")
	
		realms=[]
		nonce=None
		charset="iso-8859-1"
		while challenge:
			m=param_re.match(challenge)
			if not m:
				self.debug("Challenge syntax error: %r" % (challenge,))
				return Abort("bad-challenge")
			challenge=m.group("rest")
			var=m.group("var")
			val=m.group("val")
			self.debug("%r: %r" % (var,val))
			if var=="realm":
				realms.append(unquote(val))
			elif var=="nonce":
				if nonce:
					self.debug("Duplicate nonce")
					return Abort("bad-challenge")
				nonce=unquote(val)
			elif var=="qop":
				qopl=unquote(val).split(",")
				if "auth" not in qopl:
					self.debug("auth not supported")
					return Abort("not-implemented")
			elif var=="charset":
				if val!="utf-8":
					self.debug("charset given and not utf-8")
					return Abort("bad-challenge")
				charset="utf-8"
			elif var=="algorithm":
				if val!="md5-sess":
					self.debug("algorithm given and not md5-sess")
					return Abort("bad-challenge")

		if not nonce:
			self.debug("nonce not given")
			return Abort("bad-challenge")

		if self.password is None:
			self.password,self.pformat=self.password_manager.get_password(
						self.username,["plain","md5:user:realm:pass"])
		if not self.password or self.pformat not in ("plain","md5:user:realm:pass"):
			self.debug("Couldn't get plain password. Password: %r Format: %r"
							% (self.password,self.pformat))
			return Abort("password-unavailable")

		params=[]
		if realms:
			realms=[unicode(r,charset) for r in realms]
			realm=self.password_manager.choose_realm(realms)
			if realm:
				if type(realm) is UnicodeType:
					try:
						realm=realm.encode(charset)
					except UnicodeError:
						self.debug("Couldn't encode realm to %r" % (charset,))
						return Abort("incompatible-charset")
				elif charset!="utf-8":
					try:
						realm=unicode(realm,"utf-8").encode(charser)
					except UnicodeError:
						self.debug("Couldn't encode realm from utf-8 to %r"
											% (charset,))
						return Abort("incompatible-charset")
				realm=quote(realm)
				params.append('realm="%s"' % (realm,))

		try:
			username=self.username.encode(charset)
		except UnicodeError:
			self.debug("Couldn't encode username to %r" % (charset,))
			return Abort("incompatible-charset")

		username=quote(username)
		params.append('username="%s"' % (username,))
			
		cnonce=self.password_manager.generate_nonce()
		cnonce=quote(cnonce)
		params.append('cnonce="%s"' % (cnonce,))

		self.nonce_count+=1
		nonce_count="%08x" % (self.nonce_count,)
		params.append('nc=%s' % (nonce_count,))
		
		params.append('qop="auth"')
	
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
				return Abort("incompatible-charset")
			authzid=quote(authzid)
		else:
			authzid=""

		if self.pformat=="md5:user:realm:pass":
			urp_hash=self.password
		else:
			urp_hash=make_urp_hash(username,realm,self.password)
			
		response=compute_response(username,realm,urp_hash,nonce,cnonce,nonce_count,
							authzid,digest_uri)

		params.append('response=%s' % (response,))

		if authzid:
			params.append('authzid="%s"' % (authzid,))
	
		return Response(string.join(params,","))

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
			realm=None
		nonce=quote(self.password_manager.generate_nonce())
		self.nonce=nonce
		params.append('nonce="%s"' % (nonce,))
		params.append('qop="auth"')
		params.append('charset=utf-8')
		params.append('algorithm=md5-sess')
		return Challenge(string.join(params,","))	
		
	def response(self,response):
		if not response:
			return Abort("not-authorized")
		
		realm=to_utf8(self.realm)
		realm=quote(realm)
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
				realms=val[1:-1]
			elif var=="cnonce":
				if cnonce:
					self.debug("Duplicate cnonce")
					return Failure("not-authorized")
				cnonce=val[1:-1]
			elif var=="qop":
				if val!='"auth"':
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
			realm=None
		digest_uri_uq=digest_uri.replace('\\','')

		password,pformat=self.password_manager.get_password(
					username_uq,realm_uq,("plain","md5:user:realm:pass"))
		if pformat=="md5:user:realm:pass":
			urp_hash=password
		elif pformat=="plain":
			print `(username,realm,password)`
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
		print `authzid`
		if self.password_manager.check_authzid(authzid_uq,info):
			rspauth=compute_response_auth(username,realm,urp_hash,self.nonce,
							cnonce,nonce_count,authzid,digest_uri)
			return Success("rspauth="+rspauth)
		else:
			self.debug("Authzid check failed")
			return Failure("not-authorized")
