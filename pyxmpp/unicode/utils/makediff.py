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
input.close()

input=open("UnicodeData-3.2.0.txt","r")
print >>output,"combining_3_2_0={"
for l in input.readlines():
        l=l.rstrip()
        try:
                code,name,x1,cc,rest=l.split(";",4)
        except:
                continue

        cc=int(cc)

        try:
                c=unichr(string.atoi(code,16))
        except ValueError:
                continue

        pcc=unicodedata.combining(c)

        if pcc!=cc:
                print >>output,"\t%r: %r," % (c,cc)
        continue

print >>output,"\t}"
input.close()


# vi: sts=4 et sw=4
