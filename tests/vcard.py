#!/usr/bin/python

import unittest

import libxml2
from pyxmpp.jabber import vcard

def vcard2txt(vcard):
    """Extract data from VCard object for text comparision.
    Separate function defined here to test the API (attribute access)."""
    ret="Full name: %r\n" % (vcard.fn.value,)
    ret+="Structural name:\n"
    ret+="  Family name: %r\n" % (vcard.n.family,)
    ret+="  Given name: %r\n" % (vcard.n.given,)
    ret+="  Middle name: %r\n" % (vcard.n.middle,)
    ret+="  Prefix: %r\n" % (vcard.n.prefix,)
    ret+="  Suffix: %r\n" % (vcard.n.suffix,)
    for nickname in vcard.nickname:
        ret+="Nickname: %r\n" % (nickname.value,)
    for photo in vcard.photo:
        ret+="Photo:\n"
        ret+="  Type: %r\n" % (photo.type,)
        ret+="  Image: %r\n" % (photo.image,)
        ret+="  URI: %r\n" % (photo.uri,)
    for bday in vcard.bday:
        ret+="Birthday: %r\n" % (bday.value,)
    for adr in vcard.adr:
        ret+="Address:\n"
        ret+="  Type: %r\n" % (adr.type,)
        ret+="  POBox: %r\n" % (adr.pobox,)
        ret+="  Extended: %r\n" % (adr.extadr,)
        ret+="  Street: %r\n" % (adr.street,)
        ret+="  Locality: %r\n" % (adr.locality,)
        ret+="  Region: %r\n" % (adr.region,)
        ret+="  Postal code: %r\n" % (adr.pcode,)
        ret+="  Country: %r\n" % (adr.ctry,)
    for label in vcard.label:
        ret+="Label:\n"
        ret+="  Type: %r\n" % (label.type,)
        ret+="  Lines: %r\n" % (label.lines,)
    for tel in vcard.tel:
        ret+="Telephone:\n"
        ret+="  Type: %r\n" % (tel.type,)
        ret+="  Number: %r\n" % (tel.number,)
    for email in vcard.email:
        ret+="E-mail:\n"
        ret+="  Type: %r\n" % (email.type,)
        ret+="  Address: %r\n" % (email.address,)
    for jid in vcard.jabberid:
        ret+="JID: %r\n" % (jid.value,)
    for mailer in vcard.mailer:
        ret+="Mailer: %r\n" % (mailer.value,)
    for tz in vcard.tz:
        ret+="Timezone: %r\n" % (tz.value,)
    for geo in vcard.geo:
        ret+="Geographical location:\n"
        ret+="  Latitude: %r\n" % (geo.lat,)
        ret+="  Longitude: %r\n" % (geo.lon,)
    for title in vcard.title:
        ret+="Title: %r\n" % (title.value,)
    for role in vcard.role:
        ret+="Role: %r\n" % (role.value,)
    for logo in vcard.logo:
        ret+="Logo:\n"
        ret+="  Type: %r\n" % (logo.type,)
        ret+="  Image: %r\n" % (logo.image,)
        ret+="  URI: %r\n" % (logo.uri,)
    for org in vcard.org:
        ret+="Organization:\n"
        ret+="  Name: %r\n" % (org.name,)
        ret+="  Unit: %r\n" % (org.unit,)
    for cat in vcard.categories:
        ret+="Categories: %r\n" % (cat.keywords,)
    for note in vcard.note:
        ret+="Note: %r\n" % (note.value,)
    for prodid in vcard.prodid:
        ret+="Product id: %r\n" % (prodid.value,)
    for rev in vcard.rev:
        ret+="Revision: %r\n" % (rev.value,)
    for sort_string in vcard.sort_string:
        ret+="Sort string: %r\n" % (sort_string.value,)
    for sound in vcard.sound:
        ret+="Sound:\n"
        ret+="  Sound: %r\n" % (sound.sound,)
        ret+="  URI: %r\n" % (sound.uri,)
        ret+="  Phonetic: %r\n" % (sound.phonetic,)
    for uid in vcard.uid:
        ret+="User id: %r\n" % (uid.value,)
    for url in vcard.url:
        ret+="URL: %r\n" % (url.value,)
    try:
        for cls in vcard["CLASS"]:
            ret+="Class: %r\n" % (cls.value,)
    except KeyError:
        pass
    for key in vcard.key:
        ret+="Key:\n"
        ret+="  Type: %r\n" % (key.type,)
        ret+="  Value: %r\n" % (key.cred,)
    for desc in vcard.desc:
        ret+="Description: %r\n" % (desc.value,)
    return ret

def xml_error_handler(ctx,error):
    pass

class TestVCard(unittest.TestCase):
    def setUp(self):
        libxml2.registerErrorHandler(xml_error_handler,None)
    def tearDown(self):
        libxml2.registerErrorHandler(None,None)
    def test_xml_input1(self):
        xmldata=libxml2.parseFile("data/vcard1.xml")
        vc=vcard.VCard(xmldata.getRootElement())
        should_be=file("data/vcard1.txt").read()
        self.failUnlessEqual(vcard2txt(vc),should_be)
    def test_xml_without_n(self):
        xmldata=libxml2.parseFile("data/vcard_without_n.xml")
        vc=vcard.VCard(xmldata.getRootElement())
        should_be=file("data/vcard_without_n.txt").read()
        self.failUnlessEqual(vcard2txt(vc),should_be)
    def test_xml_without_fn(self):
        xmldata=libxml2.parseFile("data/vcard_without_n.xml")
        vc=vcard.VCard(xmldata.getRootElement())
        should_be=file("data/vcard_without_n.txt").read()
        self.failUnlessEqual(vcard2txt(vc),should_be)
    def test_xml_with_semicolon(self):
        xmldata = libxml2.parseFile("data/vcard_with_semicolon.xml")
        vc = vcard.VCard(xmldata.getRootElement())
        first = vc.rfc2426()
        second = vcard.VCard(first).rfc2426()
        self.failUnlessEqual(first, second)
    def test_vcf_input1(self):
        input=file("data/vcard2.vcf").read()
        vc=vcard.VCard(input)
        should_be=file("data/vcard2.txt").read()
        self.failUnlessEqual(vcard2txt(vc),should_be)
    def test_vcf_input2(self):
        input=file("data/vcard3.vcf").read()
        vc=vcard.VCard(input)
        should_be=file("data/vcard3.txt").read()
        self.failUnlessEqual(vcard2txt(vc),should_be)
    #TODO: test_xml_output

def suite():
     suite = unittest.TestSuite()
     suite.addTest(unittest.makeSuite(TestVCard))
     return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

# vi: sts=4 et sw=4
