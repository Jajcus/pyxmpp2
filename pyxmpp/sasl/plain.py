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

__revision__="$Id: plain.py,v 1.8 2004/09/10 13:18:55 jajcus Exp $"

import logging

from pyxmpp.utils import to_utf8,from_utf8
from pyxmpp.sasl.core import ClientAuthenticator,ServerAuthenticator
from pyxmpp.sasl.core import Success,Failure,Challenge,Response

class PlainClientAuthenticator(ClientAuthenticator):
    def __init__(self,password_manager):
        ClientAuthenticator.__init__(self,password_manager)
        self.__logger=logging.getLogger("pyxmpp.sasl.PlainClientAuthenticator")
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
            self.__logger.debug("Already authenticated")
            return Failure("extra-challenge")
        self.finished=1
        if self.password is None:
            self.password,pformat=self.password_manager.get_password(self.username)
        if not self.password or pformat!="plain":
            self.__logger.debug("Couldn't retrieve plain password")
            return Failure("password-unavailable")
        return Response("%s\000%s\000%s" % (    to_utf8(self.authzid),
                            to_utf8(self.username),
                            to_utf8(self.password)))

class PlainServerAuthenticator(ServerAuthenticator):
    def __init__(self,password_manager):
        ServerAuthenticator.__init__(self,password_manager)
        self.__logger=logging.getLogger("pyxmpp.sasl.PlainServerAuthenticator")
    def start(self,response):
        if not response:
            return Challenge("")
        return self.response(response)
    def response(self,response):
        s=response.split("\000")
        if len(s)!=3:
            self.__logger.debug("Bad response: %r" % (response,))
            return Failure("not-authorized")
        authzid,username,password=s

        authzid=from_utf8(authzid)
        username=from_utf8(username)
        password=from_utf8(password)

        if not self.password_manager.check_password(username,password):
            self.__logger.debug("Bad password. Response was: %r" % (response,))
            return Failure("not-authorized")

        info={"mechanism":"PLAIN","username":username}
        if self.password_manager.check_authzid(authzid,info):
            return Success(username,None,authzid)
        else:
            self.__logger.debug("Authzid verification failed.")
            return Failure("invalid-authzid")
# vi: sts=4 et sw=4
