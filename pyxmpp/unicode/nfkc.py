
import unicodedata,string
import sys

from cexc import composition_exclusions
from ccomp import canonical_comp
from ud_3_2_0 import decompositions_3_2_0

class UnicodeNormalizationError(StandardError):
	pass


SBase = 0xAC00
LBase = 0x1100
VBase = 0x1161
TBase = 0x11A7
LCount = 19
VCount = 21
TCount = 28
NCount = VCount * TCount
SCount = LCount * NCount

def hangul_decompose(c):
	s=ord(c)
	SIndex=s-SBase

	if SIndex<0 or SIndex>=SCount:
		return c

	L=LBase+SIndex/NCount
	V=VBase+(SIndex%NCount)/TCount
	T=TBase+SIndex%TCount
	res=[unichr(L),unichr(V)]
	if T!=TBase: res.append(unichr(T))
	return res


def decompose(c):
	s=ord(c)
	if s>=SBase and s-SBase<SCount:
		return hangul_decompose(c)

	d=decompositions_3_2_0.get(c,unicodedata.decomposition(c))
	
	if not d:
		return [c]
	if d.startswith("<"):
		d=d[d.index(">")+1:]
		print "Compatibility decomposition: %r -> %r" % (c,d)
	else:
		print "Canonical decomposition: %r -> %r" % (c,d)
	
	ret=[]
	for c in d.split():
		ret+=decompose(unichr(string.atoi(c,16)))
		
	return ret


def hangul_compose(l):
	if not l:
		return l
	ll=len(l)
	last=ord(l[0][2])
	result=[l[0]]

	for i in range(1,ll):
		lch=l[i]
		ch=ord(lch[2])

		LIndex=last-LBase
		if 0<=LIndex and LIndex<LCount:
			VIndex=ch-VBase
			if 0<=VIndex and VIndex<VCount:
				last=(SBase+(LIndex*VCount+VIndex)*TCount)
				result[-1]=(0,lch[1],unichr(last))
				continue

		SIndex=last-SBase
		if 0<=SIndex and SIndex<SCount and (SIndex%SCount)==0:
			TIndex=ch-TBase
			if 0<=TIndex and TIndex<=TCount:
				last+=TIndex
				result[-1]=(0,lch[1],unichr(last))
				continue

		last=ch
		result.append(lch)
	return result

def composetwo(a,b):

	if canonical_comp.has_key(a+b):
		r=canonical_comp[a+b]
		if composition_exclusions.has_key(r):
			return None
		return canonical_comp[a+b]
	else:
		return None

def compose(l):
	l=hangul_compose(l)
	Li=None
	i=0
	while i<len(l):
		C=l[i]
		print "%i: C=%r, l=%r, Li=%r" % (i,C,l,Li)
		if Li is not None and i>0 and ((l[i-1][0]!=0 and l[i-1][0]!=C[0]) or Li==i-1):
			L=l[Li]
			print "trying to compose %r and %r" % (C,L)
			LC=composetwo(L[2],C[2])
			if LC:
				l[Li]=unicodedata.combining(LC),C[1],LC
				l[i:]=l[i+1:]
		else:
			if Li is not None:
				print "not composing %r and %r" % (C,l[Li])
			LC=None
		if LC is None:
			if C[0]==0:
				Li=i
			i+=1
	ret=[c for a,b,c in l]
	return ret

def NFKC(input):
	decomp=[]
	for c in input:
		decomp+=decompose(c)
	
	print "Decomposition:",`decomp`

	cdecomp=[]
	tmp=[]
	i=0
	for c in decomp:
		cc=unicodedata.combining(c)
		if cc==0:
			if tmp:
				tmp.sort()
				cdecomp+=tmp
			tmp=[(cc,i,c)]
		else:
			tmp.append((cc,i,c))
		i+=1
	tmp.sort()
	cdecomp+=tmp

	print "Canonical decomposition:",`cdecomp`

	ret=compose(cdecomp)
	
	ret=string.join(ret,"")
	print "Result:",`ret`
	return ret
