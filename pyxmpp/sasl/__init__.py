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

from core import Reply,Response,Challenge,Success,Failure,PasswordManager

from plain import PlainClientAuthenticator,PlainServerAuthenticator
from digest_md5 import DigestMD5ClientAuthenticator,DigestMD5ServerAuthenticator

safe_mechanisms_dict={"DIGEST-MD5":(DigestMD5ClientAuthenticator,DigestMD5ServerAuthenticator)}
unsafe_mechanisms_dict={"PLAIN":(PlainClientAuthenticator,PlainServerAuthenticator)}
all_mechanisms_dict=safe_mechanisms_dict.copy()
all_mechanisms_dict.update(unsafe_mechanisms_dict)

safe_mechanisms=safe_mechanisms_dict.keys()
unsafe_mechanisms=unsafe_mechanisms_dict.keys()
all_mechanisms=safe_mechanisms+unsafe_mechanisms

def ClientAuthenticator(mechanism,password_manager):
	authenticator=all_mechanisms_dict[mechanism][0]
	return authenticator(password_manager)

def ServerAuthenticator(mechanism,password_manager):
	authenticator=all_mechanisms_dict[mechanism][1]
	return authenticator(password_manager)
