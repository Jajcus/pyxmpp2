#!/usr/bin/python 

import string
import unicodedata

try:
	input=open("UnicodeData-3.2.0.txt","r")
except:
	print >>sys.stderr,"Normalization test data not available - trying to download"
	os.system("wget http://www.unicode.org/Public/3.2-Update/UnicodeData-3.2.0.txt")
	input=open("UnicodeData-3.2.0.txt","r")


output=open("../ud_3_2_0.py","w")

print >>output,"decompositions_3_2_0={"
for l in input.readlines():
	l=l.rstrip()
	try:
		code,name,x1,x2,x3,comp,rest=l.split(";",6)
	except:
		continue

	try:
		c=unichr(string.atoi(code,16))
	except ValueError:
		continue
		
	pcomp=unicodedata.decomposition(c)
	
	if pcomp!=comp:
		print >>output,"\t%r: %r," % (c,comp)
	continue
	
print >>output,"\t}"

