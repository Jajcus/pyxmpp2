from core import ClientAuthenticator
from core import ServerAuthenticator

class PlainClientAuthenticator(ClientAuthenticator):
	def start(self,username,authzid,password=None):
		self.username=username
		if authzid:
			self.authzid=authzid
		else:
			self.authzid=""
		self.password=password
		self.finished=0
		return self.challenge("")
	
	def challenge(self,challenge):
		if not challenge:
			self.debug("Empty challenge")
			return Abort("bad-challenge")
		if self.finished:
			self.debug("Already authenticated")
			return Abort("extra-challenge")
		self.finished=1
		if self.password is None:
			self.password,pformat=self.get_password(username)
		if not self.password or pformat!="plain":
			self.debug("Couldn't retrieve plain password")
			return Abort("password-unavailable")
		return Response("%s\000%s\000%s" % (	to_utf8(self.authzid),
							to_utf8(self.username),
							to_utf8(self.password)))

class PlainServerAuthenticator(ServerAuthenticator):
	def start(self,response):
		if not reponse:
			return Challenge("")
		self.response(response)
	def response(self,response):
		s=response.split("\000")
		if len(s)!=3:
			self.debug("Bad response: %r" % (response,))
			return Failure("not-authorized")
		authzid,username,password=s
		if not self.password_manager.check_password(from_utf8(response)):
			self.debug("Bad password. Response was: %r" % (response,))
			return Failure("not-authorized")
		return Success(authzid)
	
