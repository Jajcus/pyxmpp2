
from types import ListType
import string

from pyxmpp.unicode.nfkc import NFKC
from rfc3454 import LookupTable
from rfc3454 import A_1,B_1,B_2,C_1_1,C_1_2,C_2_1,C_2_2,C_3,C_4,C_5,C_6,C_7,C_8,C_9,D_1,D_2

""" Stringprep (RFC3454) implementation with nodeprep and resourceprep profiles."""

class StringprepError(StandardError):
	"""Exception raised when string preparation results in error."""
	pass

class Profile:
	"""Base class for stringprep profiles."""
	def __init__(self,unassigned,mapping,normalization,prohibited,bidi=1):
		""" Profile(unassigned,mapping,normalization,prohibited,bidi=1) -> Profile

		Constructor for a stringprep profile object.

		unassigned is a lookup table with unassigned codes
		mapping is a lookup table with character mappings
		normalization is a normalization function
		prohibited is a lookup table with prohibited characters
		bidi if 1 means bidirectional checks should be done
		"""
		self.unassigned=unassigned
		self.mapping=mapping
		self.normalization=normalization
		self.prohibited=prohibited
		self.bidi=bidi
		
	def prepare(self,s):
		"""Complete string preparation procedure for 'stored' strings.
		(includes checks for unassigned codes)"""
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
		"""Complete string preparation procedure for 'query' strings.
		(without checks for unassigned codes)"""
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
		"""Mapping part of string preparation."""
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
		"""Checks for prohibited characters."""
		for c in s:
			for t in self.prohibited:
				if t.lookup(c) is not None:
					raise StringprepError,"Prohibited character: %r" % (c,)
		return s
	
	def check_unassigned(self,s):
		"""Checks for unassigned character codes."""
		for c in s:
			for t in self.unassigned:
				if t.lookup(c) is not None:
					raise StringprepError,"Unassigned character: %r" % (c,)
		return s
	
	def check_bidi(self,s):
		"""Checks if sting is valid for bidirectional printing."""
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

