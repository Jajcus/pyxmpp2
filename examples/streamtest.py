#!/usr/bin/python

import sys,os
from pyxmpp import xmlextra

h=xmlextra.StreamHandler()
r=xmlextra.StreamReader(h)
print dir(r.reader)

while 1:
	r.feed(os.read(sys.stdin.fileno(),100))

del r

