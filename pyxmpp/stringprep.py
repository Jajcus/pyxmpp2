
from types import ListType
import string

from pyxmpp.unicode.nfkc import NFKC
from rfc3454 import LookupTable
from rfc3454 import A_1,B_1,B_2,C_1_1,C_1_2,C_2_1,C_2_2,C_3,C_4,C_5,C_6,C_7,C_8,C_9,D_1,D_2


class StringprepError(StandardError):
	pass

class Profile:
	def __init__(self,unassigned,mapping,normalization,prohibited,bidi=1):
		self.unassigned=unassigned
		self.mapping=mapping
		self.normalization=normalization
		self.prohibited=prohibited
		self.bidi=bidi
		
	def prepare(self,s):
		s=self.map(s)
		if self.normalization:
			s=self.normalization(s)
		s=self.prohibit(s)
		s=self.check_unassigned(s)
		if self.bidi:
			s=self.check_bidi(s)
		if type(s) is ListType:
			s=string.join(s)
		return s

	def prepare_query(self,s):
		s=self.map(s)
		if self.normalization:
			s=self.normalization(s)
		s=self.prohibit(s)
		if self.bidi:
			s=self.check_bidi(s)
		if type(s) is ListType:
			s=string.join(s)
		return s

	def map(self,s):
		r=[]
		for c in s:
			rc=None
			for t in self.mapping:
				rc=t.lookup(c)
				if rc is not None:
					break
			if rc is not None:
				r.append(rc)
			else:
				r.append(c)
		return r

	def prohibit(self,s):
		for c in s:
			for t in self.prohibited:
				if t.lookup(c) is not None:
					raise StringprepError,"Prohibited character: %r" % (c,)
		return s
	
	def check_unassigned(self,s):
		for c in s:
			for t in self.unassigned:
				if t.lookup(c) is not None:
					raise StringprepError,"Unassigned character: %r" % (c,)
		return s
	
	def check_bidi(self,s):
		has_L=0
		has_RAL=0
		for c in s:
			if D_1.lookup(c) is not None:
				has_RAL=1
			elif D_2.lookup(c) is not None:
				has_L=1
		if has_L and has_RAL:
			raise StringprepError,"Both RandALCat and LCat characters present"
		if has_RAL and (D_1.lookup(s[0]) is None or D_1.lookup(s[-1]) is None):
			raise StringprepError,"The first and the last character must be RandALCat"
		return s

nodeprep=Profile(
	unassigned=(A_1,),
	mapping=(B_1,B_2),
	normalization=NFKC,
	prohibited=(C_1_1,C_1_2,C_2_1,C_2_2,C_3,C_4,C_5,C_6,C_7,C_8,C_9,
			LookupTable({u'"':1,u'&':1,u"'":1,u"/":1,u":":1,u"<":1,u">":1,u"@":1},()) ),
	bidi=1)

resourceprep=Profile(
	unassigned=(A_1,),
	mapping=(B_1,),
	normalization=NFKC,
	prohibited=(C_1_2,C_2_1,C_2_2,C_3,C_4,C_5,C_6,C_7,C_8,C_9),
	bidi=1)

