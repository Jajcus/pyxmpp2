#!/usr/bin/python

import libxml2
from pyxmpp.jabber import vcard

xmldata=libxml2.parseFile("vcard1.xml")
textdata=file("vcard2.vcf").read()

vc1=vcard.VCard(xmldata.getRootElement())
print `vc1`
file("vcard1.out.vcf","w").write(vc1.rfc2426())
file("vcard1.out.xml","w").write(vc1.xml().serialize(encoding="utf-8"))

vc2=vcard.VCard(textdata)
print `vc2`
file("vcard2.out.vcf","w").write(vc2.rfc2426())

doc=libxml2.newDoc("1.0")
root=doc.newChild(None,"root",None)
vc2.xml(parent=root)
file("vcard2.out.xml","w").write(doc.serialize(encoding="utf-8"))


vc3=vcard.VCard(file("vcard3.vcf").read())
print `vc3`
file("vcard3.out.vcf","w").write(vc3.rfc2426())

doc=libxml2.newDoc("1.0")
root=doc.newChild(None,"root",None)
root.newNs("vcard-temp","vcard")
vc3.xml(doc,root)
file("vcard3.out.xml","w").write(doc.serialize(encoding="utf-8"))

# vi: sts=4 et sw=4
