
from types import UnicodeType

def to_utf8(s):
	if type(s) is UnicodeType:
		return s.encode("utf-8")
	else:
		return str(s)
	
def from_utf8(s):
	if type(s) is UnicodeType:
		return s
	else:
		return unicode(s,"utf-8")

