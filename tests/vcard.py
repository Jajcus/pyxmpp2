#!/usr/bin/python

import libxml2
from pyxmpp.jabber import vcard

xmldata=libxml2.parseFile("vcard1.xml")
textdata=file("vcard2.txt").read()

vc1=vcard.VCard(xmldata.getRootElement())
print `vc1`
file("vcard1.out.txt","w").write(vc1.rfc2426())
vc2=vcard.VCard(textdata)
print `vc2`
file("vcard2.out.txt","w").write(vc2.rfc2426())
