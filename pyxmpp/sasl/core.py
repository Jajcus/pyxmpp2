import random
import string
import sys

class PasswordManager:
	def get_password(self,username,realm=None,acceptable_format=("plain",)):
		return None,None
	def check_password(self,username,password,realm=None):
		pw,format=self.get_password(username,realm)
		if pw and format=="plain" and p==password:
			return 1
		return 0
	def get_realms(self):
		return None
	def choose_realm(self,realm_list):
		return realm_list[0]
	def check_authzid(self,authzid,extra_info={}):
		return extra_info.has_key("username") and username==authzid

	def get_serv_type(self):
		return "unknown"
	def get_serv_host(self):
		return "unknown"
	def get_serv_name(self):
		return None
	
	def generate_nonce(self):
		r1=str(random.random())[2:]
		r2=str(random.random())[2:]
		return r1+r2

class Reply:
	pass

class Abort(Reply):
	def __init__(self,reason):
		self.reason=reason
	def __repr__(self):
		return "<sasl.Abort: %r>" % (self.reason,)

class Response(Reply):
	def __init__(self,response=""):
		self.response=response
	def __str__(self):
		return self.response
	def __repr__(self):
		return "<sasl.Response: %r>" % (self.response,)

class ClientAuthenticator:
	def __init__(self,password_manager):
		self.password_manager=password_manager
	def start(self,username,authzid):
		return Abort("Not implemented")
	def challenge(self,challenge):
		return Abort("Not implemented")
	def debug(self,s):
		print >>sys.stderr,"SASL client:",self.__class__,s
	
class Challenge(Reply):
	def __init__(self,challenge):
		self.challenge=challenge
	def __str__(self):
		return self.challenge
	def __repr__(self):
		return "<sasl.Challenge: %r>" % (self.challenge,)

class Failure(Reply):
	def __init__(self,reason):
		self.reason=reason
	def __str__(self):
		return self.reason
	def __repr__(self):
		return "<sasl.Failure: %r>" % (self.reason,)

class Success(Reply):
	def __init__(self,authzid,data=None):
		self.authzid=authzid
		self.data=None
	def get_authzid(self):
		return self.authzid
	def __repr__(self):
		return "<sasl.Success: authzid: %r data: %r>" % (self.authzid,self.data)

class ServerAuthenticator:
	def __init__(self,password_manager):
		self.password_manager=password_manager
	def start(self,initial_response):
		return Failure("not-authorized")
	def response(self,response):
		return Failure("not-authorized")
	def debug(self,s):
		print >>sys.stderr,"%s: %s" % (self.__class__,s)
