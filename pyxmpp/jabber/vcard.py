#
# (C) Copyright 2003 Jacek Konieczny <jajcus@bnet.pl>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import base64
import binascii
import libxml2
import re

from pyxmpp.utils import to_utf8,from_utf8

valid_string_re=re.compile(r"^[\w\d \t]*$")

def rfc2425encode(type,value,parameters,charset="utf-8"):
	if type(value) is types.UnicodeType:
		value=value.replace(u"\r\n",u"\\n")
		value=value.replace(u"\n",u"\\n")
		value=value.replace(u"\r",u"\\n")
		value=value.encode(charset,"replace")
	elif type(value) is not types.StringType:
		raise TypeError,"Bad type for rfc2425 value"
	elif not valid_string_re.match(value):
		parameters["encoding"]="b"
		value=binascii.b2a_base64(value)
	
	ret=type
	for k,v in parameters.items():
		ret+="%s;%s" % (k,v)
	ret+=":"
	while(len(value)>70):
		ret+=value[:70]+"\r\n "
	ret+=value+"\r\n"
	return ret
	
class VCardString:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if isinstance(value,libxml2.xmlNone):
			self.value=unicode(value.getContent(),"utf-8","replace")
		else:
			self.value=value
	def rfc2426(self):
		return rfc2425encode(self.name,self.value)
	def xml(self,parent):
		return parent.newTextChild(parent.ns(),to_utf8(self.name.upper()),value)

class VCardName:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="N":
			raise RuntimeError,"VCardName handles only 'N' type"
		if isinstance(value,libxml2.xmlNone):
			self.family,self.given,self.middle,self.prefix,self.suffix=[""]*5
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='FAMILY':
					self.family=unicode(n.getContent(),"utf-8")
				if n.name=='GIVEN':
					self.given=unicode(n.getContent(),"utf-8")
				if n.name=='MIDDLE':
					self.middle=unicode(n.getContent(),"utf-8")
				if n.name=='PREFIX':
					self.prefix=unicode(n.getContent(),"utf-8")
				if n.name=='SUFFIX':
					self.suffix=unicode(n.getContent(),"utf-8")
		else:
			value=[""]*5
			v=value.split(";")
			value[:len(v)]=v
			self.family,self.given,self.middle,self.prefix,self.suffix=value
	def rfc2426(self):
		return rfc2425encode("n","%s;%s;%s;%s" % 
				(self.family,self.given,self.middle,self.prefix,self.suffix))
	def xml(self,parent):
		n=parent.newChild(parent.ns(),"N",None)
		n.newTextChild(n.ns(),"FAMILY",to_utf8(self.family))
		n.newTextChild(n.ns(),"GIVEN",to_utf8(self.given))
		n.newTextChild(n.ns(),"MIDDLE",to_utf8(self.middle))
		n.newTextChild(n.ns(),"PREFIX",to_utf8(self.prefix))
		n.newTextChild(n.ns(),"SUFFIX",to_utf8(self.suffix))
		return n

class VCardImage:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if isinstance(value,libxml2.xmlNone):
			self.uri,self.type,self.image=[None]*3
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='TYPE':
					self.type=unicode(n.getContent(),"utf-8","replace")
				if n.name=='BINVAL':
					self.image=base64.decodestring(n.getContent())
				if n.name=='EXTVAL':
					self.uri=unicode(n.getContent(),"utf-8","replace")
			if (self.uri and self.image) or (not self.uri and not self.image):
				raise ValueError,"Bad %s value in vcard" % (name,)
		else:
			if rfc2425parameters.get("value").lower()=="uri":
				self.uri=value
				self.type=None
			else:
				self.type=rfc2425parameters.get("type")
				self.image=value
	def rfc2426(self):
		if self.uri:
			return rfc2425encode(self.name,self.uri,{"value":"uri"})
		elif self.image:
			if self.type:
				p={"type":self.type}
			else:
				p={}
			return rfc2425encode(self.name,self.image,p)
	def xml(self,parent):
		n=parent.newChild(parent.ns(),self.name.upper(),None)
		if self.uri:
			n.newTextChild(n.ns(),"EXTVAL",to_utf8(self.uri))
		else:
			if self.type:
				n.newTextChild(n.ns(),"TYPE",self.type)
			n.newTextChild(n.ns(),"BINVAL",binascii.b2a_base64(self.image))
		return n

class VCardAdr:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="ADR":
			raise RuntimeError,"VCardAdr handles only 'ADR' type"
		if isinstance(value,libxml2.xmlNone):
			(self.pobox,self.extadr,self.street,self.locality,
					self.region,self.pcode,self.ctry)=[""]*7
			self.type=[]
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='POBOX':
					self.pobox=unicode(n.getContent(),"utf-8","replace")
				elif n.name=='EXTADR':
					self.extadr=unicode(n.getContent(),"utf-8","replace")
				elif n.name=='STREET':
					self.street=unicode(n.getContent(),"utf-8","replace")
				elif n.name=='LOCALITY':
					self.locality=unicode(n.getContent(),"utf-8","replace")
				elif n.name=='REGION':
					self.region=unicode(n.getContent(),"utf-8","replace")
				elif n.name=='PCODE':
					self.pcode=unicode(n.getContent(),"utf-8","replace")
				elif n.name=='CTRY':
					self.ctry=unicode(n.getContent(),"utf-8","replace")
				elif n.name in ("HOME","WORK","POSTAL","PARCEL","DOM","INTL",
						"PREF"):
					self.type.append(n.name.lower())
			if self.type==[]:
				self.type=["intl","postal","parcel","work"]
			elif "dom" in self.type and "intl" in self.type:
				raise ValueError,"Both 'dom' and 'intl' specified in vcard ADR"
		else:
			t=rfc2425parameters.get("type")
			if t:
				self.type=t.split(",")
			else:
				self.type=["intl","postal","parcel","work"]
			value=[""]*7
			v=value.split(";")
			value[:len(v)]=v
			(self.pobox,self.extadr,self.street,self.locality,
					self.region,self.pcode,self.ctry)=value

	def rfc2426(self):
		return rfc2425encode("adr",u"%s;%s;%s;%s;%s;%s;%s" % 
				(self.pobox,self.extadr,self.street,self.locality,
						self.region,self.pcode,self.ctry),
				{"type":string.join(self.type,",")})
	def xml(self,parent):
		n=parent.newChild(parent.ns(),"ADR",None)
		for t in ("home","work","postal","parcel","dom","intl","pref"):
			if t in self.type:
				n.newChild(n.ns(),t.upper(),None)
		n.newTextChild(n.ns(),"POBOX",to_utf8(self.pobox))
		n.newTextChild(n.ns(),"EXTADR",to_utf8(self.extadr))
		n.newTextChild(n.ns(),"STREET",to_utf8(self.street))
		n.newTextChild(n.ns(),"LOCALITY",to_utf8(self.locality))
		n.newTextChild(n.ns(),"REGION",to_utf8(self.region))
		n.newTextChild(n.ns(),"PCODE",to_utf8(self.pcode))
		n.newTextChild(n.ns(),"CTRY",to_utf8(self.ctry))
		return n

class VCardLabel:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="LABEL":
			raise RuntimeError,"VCardAdr handles only 'LABEL' type"
		if isinstance(value,libxml2.xmlNone):
			self.lines=[]
			self.type=[]
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='LINE':
					l=unicode(n.getContent(),"utf-8","replace").strip()
					l=l.replace("\n"," ").replace("\r"," ")
					self.lines.append(l)
				elif n.name in ("HOME","WORK","POSTAL","PARCEL","DOM","INTL",
						"PREF"):
					self.type.append(n.name.lower())
			if self.type==[]:
				self.type=["intl","postal","parcel","work"]
			elif "dom" in self.type and "intl" in self.type:
				raise ValueError,"Both 'dom' and 'intl' specified in vcard LABEL"
			if not self.lines:
				self.lines=[""]
		else:
			t=rfc2425parameters.get("type")
			if t:
				self.type=t.split(",")
			else:
				self.type=["intl","postal","parcel","work"]
			self.lines=value.split("\\n")

	def rfc2426(self):
		return rfc2425encode("label",string.join(self.lines,"\n"),
				{"type":string.join(self.type,",")})
	def xml(self,parent):
		n=parent.newChild(parent.ns(),"ADR",None)
		for t in ("home","work","postal","parcel","dom","intl","pref"):
			if t in self.type:
				n.newChild(n.ns(),t.upper(),None)
		for l in self.lines:
			n.newTextChild(n.ns(),"LINE",l)
		return n

class VCardTel:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="TEL":
			raise RuntimeError,"VCardTel handles only 'TEL' type"
		if isinstance(value,libxml2.xmlNone):
			number=None
			self.type=[]
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='NUMBER':
					self.number=unicode(n.getContent(),"utf-8","replace")
				elif n.name in ("HOME","WORK","VOICE","FAX","PAGER","MSG",
						"CELL","VIDEO","BBS","MODEM","ISDN","PCS",
						"PREF"):
					self.type.append(n.name.lower())
			if self.type==[]:
				self.type=["voice"]
		else:
			t=rfc2425parameters.get("type")
			if t:
				self.type=t.split(",")
			else:
				self.type=["voice"]
			self.number=value
	def rfc2426(self):
		return rfc2425encode("tel",self.number,{"type":string.join(self.type,",")})
	def xml(self,parent):
		n=parent.newChild(parent.ns(),"TEL",None)
		for t in ("home","work","voice","fax","pager","msg","cell","video",
				"bbs","modem","isdn","pcs","pref"):
			if t in self.type:
				n.newChild(n.ns(),t.upper(),None)
		n.newTextChild(n.ns(),"NUMBER",to_utf8(self.number))
		return n

class VCardEmail:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="EMAIL":
			raise RuntimeError,"VCardEmail handles only 'EMAIL' type"
		if isinstance(value,libxml2.xmlNone):
			number=None
			self.type=[]
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='USERID':
					self.address=unicode(n.getContent(),"utf-8","replace")
				elif n.name in ("HOME","WORK","INTERNET","X400"):
					self.type.append(n.name.lower())
			if self.type==[]:
				self.type=["internet"]
		else:
			t=rfc2425parameters.get("type")
			if t:
				self.type=t.split(",")
			else:
				self.type=["internet"]
			self.address=value
	def rfc2426(self):
		return rfc2425encode("email",self.address,{"type":string.join(self.type,",")})
	def xml(self,parent):
		n=parent.newChild(parent.ns(),"EMAIL",None)
		for t in ("home","work","internet","x400"):
			if t in self.type:
				n.newChild(n.ns(),t.upper(),None)
		n.newTextChild(n.ns(),"USERID",to_utf8(self.address))
		return n

class VCardGeo:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="GEO":
			raise RuntimeError,"VCardName handles only 'GEO' type"
		if isinstance(value,libxml2.xmlNone):
			self.lat,self.lon=[None]*2
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='LAT':
					self.lat=unicode(n.getContent(),"utf-8")
				if n.name=='LON':
					self.lon=unicode(n.getContent(),"utf-8")
			if not self.lat or not self.lon:
				raise ValueError,"Bad vcard GEO value"
		else:
			self.lat,self.lon=value.split(";")
	def rfc2426(self):
		return rfc2425encode("geo","%s;%s" % 
				(self.lat,self.lon))
	def xml(self,parent):
		n=parent.newChild(parent.ns(),"GEO",None)
		n.newTextChild(n.ns(),"LAT",to_utf8(self.lat))
		n.newTextChild(n.ns(),"LON",to_utf8(self.lon))
		return n

class VCardOrg:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="ORG":
			raise RuntimeError,"VCardName handles only 'ORG' type"
		if isinstance(value,libxml2.xmlNone):
			self.lat,self.lon=[None]*2
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='ORGNAME':
					self.name=unicode(n.getContent(),"utf-8")
				if n.name=='ORGUNIT':
					self.unit=unicode(n.getContent(),"utf-8")
			if not self.lat or not self.lon:
				raise ValueError,"Bad vcard ORG value"
		else:
			self.name,self.unit=value.split(";")
	def rfc2426(self):
		return rfc2425encode("org","%s;%s" % 
				(self.name,self.unit))
	def xml(self,parent):
		n=parent.newChild(parent.ns(),"ORG",None)
		n.newTextChild(n.ns(),"ORGNAME",to_utf8(self.name))
		n.newTextChild(n.ns(),"ORGUNIT",to_utf8(self.unit))
		return n

class VCardCategories:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="CATEGORIES":
			raise RuntimeError,"VCardName handles only 'CATEGORIES' type"
		if isinstance(value,libxml2.xmlNone):
			self.keywords=[]
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='KEYWORD':
					self.keywords.append(unicode(n.getContent(),"utf-8"))
			if not self.keywords:
				raise ValueError,"Bad vcard CATEGORIES value"
		else:
			self.keywords=value.split(",")
	def rfc2426(self):
		return rfc2425encode("keywords",string.join(self.keywords,","))
	def xml(self,parent):
		n=parent.newChild(parent.ns(),"CATEGORIES",None)
		for k in self.keywords:
			n.newTextChild(n.ns(),"KEYWORD",to_utf8(k))
		return n

class VCardSound:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if isinstance(value,libxml2.xmlNone):
			self.uri,self.sound,self.phonetic=[None]*3
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='BINVAL':
					if (self.phonetic or self.uri):
						raise Value,"Bad SOUND value in vcard"
					self.sound=base64.decodestring(n.getContent())
				if n.name=='PHONETIC':
					if (self.sound or self.uri):
						raise Value,"Bad SOUND value in vcard"
					self.phonetic=unicode(n.getContent(),"utf-8","replace")
				if n.name=='EXTVAL':
					if (self.phonetic or self.sound):
						raise Value,"Bad SOUND value in vcard"
					self.uri=unicode(n.getContent(),"utf-8","replace")
			if (not self.phonetic and not self.image and not self.sound):
				raise Value,"Bad SOUND value in vcard"
		else:
			if rfc2425parameters.get("value").lower()=="uri":
				self.uri=value
				self.sound=None
				self.phonetic=None
			else:
				self.sound=value
				self.uri=None
				self.phonetic=None
	def rfc2426(self):
		if self.uri:
			return rfc2425encode(self.name,self.uri,{"value":"uri"})
		elif self.sound:
			return rfc2425encode(self.name,self.sound)
	def xml(self,parent):
		n=parent.newChild(parent.ns(),self.name.upper(),None)
		if self.uri:
			n.newTextChild(n.ns(),"EXTVAL",to_utf8(self.uri))
		elif self.phonetic:
			n.newTextChild(n.ns(),"PHONETIC",to_utf8(self.phonetic))
		else:
			n.newTextChild(n.ns(),"BINVAL",binascii.b2a_base64(self.image))
		return n

class VCardPrivacy:
	def __init__(self,name,value,rfc2425parameters={}):
		if isinstance(value,libxml2.xmlNone):
			self.value=None
			for n in value.get_children():
				if n.type!='element':
					continue
				if (n.ns() and value.ns() 
						and n.ns().getContent()!=value.ns().getContent()):
					continue
				if n.name=='PUBLIC':
					self.value="public"
				elif n.name=='PRIVATE':
					self.value="private"
				elif n.name=='CONFIDENTAL':
					self.value="confidental"
			if not self.value:
				raise ValueError,"Bad PRIVACY value in vcard"
		else:
			self.value=value
	def rfc2426(self):
		return rfc2425encode(self.name,self.value)
	def xml(self,parent):
		if self.value in ("public","private","confidental"):
			n=parent.newChild(parent.ns(),self.name.upper(),None)
			n.newChild(n.ns(),self.value.upper(),None)
			return n
		return None

class VCardKey(VCardItem):
	pass

class VCard(VCardItem):
	components=(
			("VERSION",VCardString,"required"),
			("FN",VCardString,"required"),
			("N",VCardName,"required"),
			("NICKNAME",VCardString,"multi"),
			("PHOTO",VCardImage,"multi"),
			("BDAY",VCardString,"multi"),
			("ADR",VCardAdr,"multi"),
			("LABEL",VCardLabel,"multi"),
			("TEL",VCardTel,"multi"),
			("EMAIL",VCardEmail,"multi"),
			("JABBERID",VCardJID,"multi"),
			("MAILER",VCardString,"multi"),
			("TZ",VCardString,"multi"),
			("GEO",VCardGeo,"multi"),
			("TITLE",VCardString,"multi"),
			("ROLE",VCardString,"multi"),
			("LOGO",VCardImage,"multi"),
			("AGENT",VCardAgent,"multi"),
			("ORG",VCardOrg,"multi"),
			("CATEGORIES",VCardCategories,"multi"),
			("NOTE",VCardString,"multi"),
			("PRODID",VCardString,"multi"),
			("REV",VCardString,"multi"),
			("SORT-STRING",VCardString,"multi"),
			("SOUND",VCardSound,"multi"),
			("UID",VCardString,"multi"),
			("URL",VCardString,"multi"),
			("CLASS",VCardString,"multi"),
			("KEY",VCardKey,"multi"),
			("DESC",VCardString,"multi")
		);
