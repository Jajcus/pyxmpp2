#!/usr/bin/python -u

import sys,os
from pyxmpp import xmlextra


h=xmlextra.StreamHandler()
r=xmlextra.StreamReader(h)
ret=None
while 1:
    data=os.read(sys.stdin.fileno(),100)
    print "."
    ret=r.feed(data)
    while ret:
        print "!"
        ret=r.feed("")
    if ret is None:
        break
# vi: sts=4 et sw=4
