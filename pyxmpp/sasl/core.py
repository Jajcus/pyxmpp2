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

import random
import string
import sys
from binascii import b2a_base64

class PasswordManager:
    def get_password(self,username,realm=None,acceptable_format=("plain",)):
        return None,None
    def check_password(self,username,password,realm=None):
        pw,format=self.get_password(username,realm)
        if pw and format=="plain" and pw==password:
            return 1
        return 0
    def get_realms(self):
        return None
    def choose_realm(self,realm_list):
        return realm_list[0]
    def check_authzid(self,authzid,extra_info={}):
        return not authzid or extra_info.has_key("username") and username==authzid

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
    def base64(self):
        if self.data is not None:
            ret=b2a_base64(self.data)
            if ret[-1]=='\n':
                ret=ret[:-1]
            return ret
        else:
            return None
class Response(Reply):
    def __init__(self,data=""):
        self.data=data
    def __repr__(self):
        return "<sasl.Response: %r>" % (self.data,)

class Challenge(Reply):
    def __init__(self,data):
        self.data=data
    def __repr__(self):
        return "<sasl.Challenge: %r>" % (self.data,)

class Failure(Reply):
    def __init__(self,reason):
        self.reason=reason
    def __repr__(self):
        return "<sasl.Failure: %r>" % (self.reason,)

class Success(Reply):
    def __init__(self,username,realm=None,authzid=None,data=None):
        self.username=username
        self.realm=realm
        self.authzid=authzid
        self.data=data
    def __repr__(self):
        return "<sasl.Success: authzid: %r data: %r>" % (self.authzid,self.data)

class ClientAuthenticator:
    def __init__(self,password_manager):
        self.password_manager=password_manager
    def start(self,username,authzid):
        return Abort("Not implemented")
    def challenge(self,challenge):
        return Abort("Not implemented")
    def finish(self,data):
        return Success(self.authzid)
    def debug(self,s):
        print >>sys.stderr,"SASL client:",self.__class__,s

class ServerAuthenticator:
    def __init__(self,password_manager):
        self.password_manager=password_manager
    def start(self,initial_response):
        return Failure("not-authorized")
    def response(self,response):
        return Failure("not-authorized")
    def debug(self,s):
        print >>sys.stderr,"%s: %s" % (self.__class__,s)
# vi: sts=4 et sw=4
