#!/usr/bin/python

import sys,os
from pyxmpp import xmlextra


h=xmlextra.StreamHandler()

for i in range(0,3):
	r=xmlextra.StreamReader(h)
	print dir(r.reader)

	try:
		while 1:
			r.feed(os.read(sys.stdin.fileno(),100))
	except:
		print "Interrupted"
