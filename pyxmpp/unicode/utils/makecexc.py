#!/usr/bin/python 

import sys
import os
import string

try:
	input=open("CompositionExclusions-3.2.0.txt","r")
except:
	print >>sys.stderr,"Composition Exclusion data not available - trying to download"
	os.system("wget http://www.unicode.org/Public/3.2-Update/CompositionExclusions-3.2.0.txt")
	input=open("CompositionExclusions-3.2.0.txt","r")

output=open("../cexc.py","w")

print >>output,"composition_exclusions={"
for l in input.readlines():
	l=l.strip()
	if l.startswith("#") or not l:
		continue

	code=l.split(None,1)[0]

	try:
		k=unichr(string.atoi(code,16))
	except ValueError:
		continue

	print >>output,"\t%r: 1," % (k,)
print >>output,"\t}"
