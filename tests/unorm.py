#!/usr/bin/python

import traceback
import sys
import string
import os

from pyxmpp.unicode.nfkc import NFKC

def num2uni(s):
	ret=u""
	for n in s.split():
		c=unichr(string.atoi(n,16))
		ret+=c
	return ret

try:
	f=open("NormalizationTest-3.2.0.txt","r")
except:
	print >>sys.stderr,"Normalization test data not available - trying to download"
	os.system("wget http://www.unicode.org/Public/3.2-Update/NormalizationTest-3.2.0.txt")
	f=open("NormalizationTest-3.2.0.txt","r")
	
for l in f.readlines():
	if l.startswith("#"):
		continue
	l=l.rstrip()

	print 
	if l.startswith("@"):
		print
		print "***",l
		continue
	h=l.find("#")
	if h>=0:
		comment=l[h:]
		p=comment.find(") ")
		if p:
			descr=comment[p+2:]
		else:
			descr="Unknown"
		l=l[0:h]
	else:
		comment=""
		descr="Unknown"
	t=l.split(";")
	c={}

	print "*** testing:",descr
	try:
		for i in range(1,6):
			c[i]=num2uni(t[i-1])
	except ValueError:
		print "!!! Skipping as the code seems too big for this python"
		continue

	for i in range(1,6):
		try:	
			print "****** NFKC(c%i) ?= c4 ..." % (i,)
			nc=NFKC(c[i])
			if nc==c[4]:
				print "********* Passed"
			else:
				print "********* Failed"
				print "!!!!!! %r != %r " % (nc,c[4])
		except (KeyboardInterrupt,SystemExit),e:
			raise
		except:
			print "!!!!!! Exception"
			traceback.print_exc(file=sys.stdout)

