#!/usr/bin/python

import sys
import os
import string
import unicodedata

try:
    input=open("UnicodeData-3.2.0.txt","r")
except:
    print >>sys.stderr,"Unicode data not available - trying to download"
    os.system("wget http://www.unicode.org/Public/3.2-Update/UnicodeData-3.2.0.txt")
    input=open("UnicodeData-3.2.0.txt","r")


output=open("../ccomp.py","w")

print >>output,"canonical_comp={"
for l in input.readlines():
    l=l.rstrip()
    try:
        code,name,x1,x2,x3,comp,rest=l.split(";",6)
    except:
        continue
    if not comp or comp.startswith("<"):
        continue

    try:
        k=u""
        for c in comp.split():
            k+=unichr(string.atoi(c,16))

        v=unichr(string.atoi(code,16))
    except ValueError:
        continue

    if len(k)==1:
        continue

    cc=unicodedata.combining(k[0])
    if cc!=0:
        continue

    print >>output,"\t%r: %r," % (k,v)
    continue
print >>output,"\t}"
# vi: sts=4 et sw=4
