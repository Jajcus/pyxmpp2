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

from pyxmpp.utils import to_utf8,from_utf8
from core import ClientAuthenticator,ServerAuthenticator,Success,Failure,Challenge,Response

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
		if self.finished:
			self.debug("Already authenticated")
			return Failure("extra-challenge")
		self.finished=1
		if self.password is None:
			self.password,pformat=self.password_manager.get_password(self.username)
		if not self.password or pformat!="plain":
			self.debug("Couldn't retrieve plain password")
			return Failure("password-unavailable")
		return Response("%s\000%s\000%s" % (	to_utf8(self.authzid),
							to_utf8(self.username),
							to_utf8(self.password)))

class PlainServerAuthenticator(ServerAuthenticator):
	def start(self,response):
		if not response:
			return Challenge("")
		return self.response(response)
	def response(self,response):
		s=response.split("\000")
		if len(s)!=3:
			self.debug("Bad response: %r" % (response,))
			return Failure("not-authorized")
		authzid,username,password=s

		authzid=from_utf8(authzid)
		username=from_utf8(username)
		password=from_utf8(password)
		
		if not self.password_manager.check_password(username,password):
			self.debug("Bad password. Response was: %r" % (response,))
			return Failure("not-authorized")
		
		info={"mechanism":"PLAIN","username":username}
		if self.password_manager.check_authzid(authzid,info):
			return Success(authzid)
		else:
			self.debug("Authzid verification failed.")
			return Failure("invalid-authzid")
