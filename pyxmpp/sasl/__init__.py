import random
import string

from core import Reply,Abort,Response,Challenge,Success,Failure,PasswordManager

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
	authenticator,None=all_mechanisms_dict[mechanism]
	return authenticator(password_manager)

def ServerAuthenticator(mechanism,password_manager):
	None,authenticator=all_mechanisms_dict[mechanism]
	return authenticator(password_manager)
