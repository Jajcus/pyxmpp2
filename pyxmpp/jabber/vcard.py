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
import types
import string

import pyxmpp.jid
from pyxmpp.utils import to_utf8,from_utf8

class Empty(Exception):
	pass

def get_node_ns(node):
	try:
		return node.ns()
	except libxml2.treeError:
		return None

valid_string_re=re.compile(r"^[\w\d \t]*$")

def rfc2425encode(name,value,parameters={},charset="utf-8"):
	if type(value) is types.UnicodeType:
		value=value.replace(u"\r\n",u"\\n")
		value=value.replace(u"\n",u"\\n")
		value=value.replace(u"\r",u"\\n")
		value=value.encode(charset,"replace")
	elif type(value) is not types.StringType:
		print `value`
		raise TypeError,"Bad type for rfc2425 value"
	elif not valid_string_re.match(value):
		parameters["encoding"]="b"
		value=binascii.b2a_base64(value)
	
	ret=name.lower()
	for k,v in parameters.items():
		ret+=";%s=%s" % (k,v)
	ret+=":"
	while(len(value)>70):
		ret+=value[:70]+"\r\n "
		value=value[70:]
	ret+=value+"\r\n"
	return ret
	
class VCardString:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if isinstance(value,libxml2.xmlNode):
			self.value=unicode(value.getContent(),"utf-8","replace").strip()
		else:
			self.value=value
		if not self.value:
			raise Empty,"Empty string value"
	def rfc2426(self):
		return rfc2425encode(self.name,self.value)
	def xml(self,parent):
		return parent.newTextChild(get_node_ns(parent),to_utf8(self.name.upper()),value)

class VCardXString(VCardString):
	def rfc2426(self):
		return rfc2425encode("x-"+self.name,self.value)

class VCardJID:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if isinstance(value,libxml2.xmlNode):
			self.value=pyxmpp.jid.JID(value.getContent())
		else:
			self.value=pyxmpp.jid.JID(value)
		if not self.value:
			raise Empty,"Empty JID value"
	def rfc2426(self):
		return rfc2425encode("x-jabberid",self.value.as_unicode())
	def xml(self,parent):
		return parent.newTextChild(get_node_ns(parent),to_utf8(self.name.upper()),self.value.as_utf8())

class VCardName:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if self.name.upper()!="N":
			raise RuntimeError,"VCardName handles only 'N' type"
		if isinstance(value,libxml2.xmlNode):
			self.family,self.given,self.middle,self.prefix,self.suffix=[u""]*5
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
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
				n=n.next
		else:
			v=value.split(";")
			value=[u""]*5
			value[:len(v)]=v
			self.family,self.given,self.middle,self.prefix,self.suffix=value
	def rfc2426(self):
		return rfc2425encode("n",u"%s;%s;%s;%s;%s" % 
				(self.family,self.given,self.middle,self.prefix,self.suffix))
	def xml(self,parent):
		ns=get_node_ns(parent)
		n=parent.newChild(ns,"N",None)
		n.newTextChild(ns,"FAMILY",to_utf8(self.family))
		n.newTextChild(ns,"GIVEN",to_utf8(self.given))
		n.newTextChild(ns,"MIDDLE",to_utf8(self.middle))
		n.newTextChild(ns,"PREFIX",to_utf8(self.prefix))
		n.newTextChild(ns,"SUFFIX",to_utf8(self.suffix))
		return n

class VCardImage:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if isinstance(value,libxml2.xmlNode):
			self.uri,self.type,self.image=[None]*3
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
					continue
				if n.name=='TYPE':
					self.type=unicode(n.getContent(),"utf-8","replace")
				if n.name=='BINVAL':
					self.image=base64.decodestring(n.getContent())
				if n.name=='EXTVAL':
					self.uri=unicode(n.getContent(),"utf-8","replace")
				n=n.next
			if (self.uri and self.image) or (not self.uri and not self.image):
				raise ValueError,"Bad %s value in vcard" % (name,)
			if (not self.uri and not self.image):
				raise Empty,"Bad %s value in vcard" % (name,)
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
		ns=get_node_ns(parent)
		n=parent.newChild(ns,self.name.upper(),None)
		if self.uri:
			n.newTextChild(ns,"EXTVAL",to_utf8(self.uri))
		else:
			if self.type:
				n.newTextChild(n.ns(),"TYPE",self.type)
			n.newTextChild(ns,"BINVAL",binascii.b2a_base64(self.image))
		return n

class VCardAdr:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if self.name.upper()!="ADR":
			raise RuntimeError,"VCardAdr handles only 'ADR' type"
		if isinstance(value,libxml2.xmlNode):
			(self.pobox,self.extadr,self.street,self.locality,
					self.region,self.pcode,self.ctry)=[""]*7
			self.type=[]
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
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
				n=n.next
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
		ns=get_node_ns(parent)
		n=parent.newChild(ns,"ADR",None)
		for t in ("home","work","postal","parcel","dom","intl","pref"):
			if t in self.type:
				n.newChild(n.ns(),t.upper(),None)
		n.newTextChild(ns,"POBOX",to_utf8(self.pobox))
		n.newTextChild(ns,"EXTADR",to_utf8(self.extadr))
		n.newTextChild(ns,"STREET",to_utf8(self.street))
		n.newTextChild(ns,"LOCALITY",to_utf8(self.locality))
		n.newTextChild(ns,"REGION",to_utf8(self.region))
		n.newTextChild(ns,"PCODE",to_utf8(self.pcode))
		n.newTextChild(ns,"CTRY",to_utf8(self.ctry))
		return n

class VCardLabel:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="LABEL":
			raise RuntimeError,"VCardAdr handles only 'LABEL' type"
		if isinstance(value,libxml2.xmlNode):
			self.lines=[]
			self.type=[]
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
					continue
				if n.name=='LINE':
					l=unicode(n.getContent(),"utf-8","replace").strip()
					l=l.replace("\n"," ").replace("\r"," ")
					self.lines.append(l)
				elif n.name in ("HOME","WORK","POSTAL","PARCEL","DOM","INTL",
						"PREF"):
					self.type.append(n.name.lower())
				n=n.next
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
		return rfc2425encode("label",string.join(self.lines,u"\n"),
				{"type":string.join(self.type,",")})
	def xml(self,parent):
		ns=get_node_ns(parent)
		n=parent.newChild(ns,"ADR",None)
		for t in ("home","work","postal","parcel","dom","intl","pref"):
			if t in self.type:
				n.newChild(ns,t.upper(),None)
		for l in self.lines:
			n.newTextChild(ns,"LINE",l)
		return n

class VCardTel:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if self.name.upper()!="TEL":
			raise RuntimeError,"VCardTel handles only 'TEL' type"
		if isinstance(value,libxml2.xmlNode):
			number=None
			self.type=[]
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
					continue
				if n.name=='NUMBER':
					self.number=unicode(n.getContent(),"utf-8","replace")
				elif n.name in ("HOME","WORK","VOICE","FAX","PAGER","MSG",
						"CELL","VIDEO","BBS","MODEM","ISDN","PCS",
						"PREF"):
					self.type.append(n.name.lower())
				n=n.next
			if self.type==[]:
				self.type=["voice"]
			if not self.number:
				raise Empty,"No tel number"
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
		ns=get_node_ns(parent)
		n=parent.newChild(ns,"TEL",None)
		for t in ("home","work","voice","fax","pager","msg","cell","video",
				"bbs","modem","isdn","pcs","pref"):
			if t in self.type:
				n.newChild(ns,t.upper(),None)
		n.newTextChild(ns,"NUMBER",to_utf8(self.number))
		return n

class VCardEmail:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if self.name.upper()!="EMAIL":
			raise RuntimeError,"VCardEmail handles only 'EMAIL' type"
		if isinstance(value,libxml2.xmlNode):
			number=None
			self.type=[]
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
					continue
				if n.name=='USERID':
					self.address=unicode(n.getContent(),"utf-8","replace")
				elif n.name in ("HOME","WORK","INTERNET","X400"):
					self.type.append(n.name.lower())
				n=n.next
			if self.type==[]:
				self.type=["internet"]
			if not self.address:
				raise Empty,"No USERID"
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
		ns=get_node_ns(parent)
		n=parent.newChild(ns,"EMAIL",None)
		for t in ("home","work","internet","x400"):
			if t in self.type:
				n.newChild(ns,t.upper(),None)
		n.newTextChild(ns,"USERID",to_utf8(self.address))
		return n

class VCardGeo:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="GEO":
			raise RuntimeError,"VCardName handles only 'GEO' type"
		if isinstance(value,libxml2.xmlNode):
			self.lat,self.lon=[None]*2
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
					continue
				if n.name=='LAT':
					self.lat=unicode(n.getContent(),"utf-8")
				if n.name=='LON':
					self.lon=unicode(n.getContent(),"utf-8")
				n=n.next
			if not self.lat or not self.lon:
				raise ValueError,"Bad vcard GEO value"
		else:
			self.lat,self.lon=value.split(";")
	def rfc2426(self):
		return rfc2425encode("geo",u"%s;%s" % 
				(self.lat,self.lon))
	def xml(self,parent):
		ns=get_node_ns(parent)
		n=parent.newChild(ns,"GEO",None)
		n.newTextChild(ns,"LAT",to_utf8(self.lat))
		n.newTextChild(ns,"LON",to_utf8(self.lon))
		return n

class VCardOrg:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if self.name.upper()!="ORG":
			raise RuntimeError,"VCardName handles only 'ORG' type"
		if isinstance(value,libxml2.xmlNode):
			self.name,self.unit=None,""
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
					continue
				if n.name=='ORGNAME':
					self.name=unicode(n.getContent(),"utf-8")
				if n.name=='ORGUNIT':
					self.unit=unicode(n.getContent(),"utf-8")
				n=n.next
			if not self.name:
				raise Empty,"Bad vcard ORG value"
		else:
			self.name,self.unit=value.split(";")
	def rfc2426(self):
		return rfc2425encode("org",u"%s;%s" % 
				(self.name,self.unit))
	def xml(self,parent):
		ns=get_node_ns(parent)
		n=parent.newChild(ns,"ORG",None)
		n.newTextChild(ns,"ORGNAME",to_utf8(self.name))
		n.newTextChild(ns,"ORGUNIT",to_utf8(self.unit))
		return n

class VCardCategories:
	def __init__(self,name,value,rfc2425parameters={}):
		if self.name.upper()!="CATEGORIES":
			raise RuntimeError,"VCardName handles only 'CATEGORIES' type"
		if isinstance(value,libxml2.xmlNode):
			self.keywords=[]
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
					continue
				if n.name=='KEYWORD':
					self.keywords.append(unicode(n.getContent(),"utf-8"))
				n=n.next
			if not self.keywords:
				raise Empty,"Bad vcard CATEGORIES value"
		else:
			self.keywords=value.split(",")
	def rfc2426(self):
		return rfc2425encode("keywords",string.join(self.keywords,u","))
	def xml(self,parent):
		ns=get_node_ns(parent)
		n=parent.newChild(ns,"CATEGORIES",None)
		for k in self.keywords:
			n.newTextChild(ns,"KEYWORD",to_utf8(k))
		return n

class VCardSound:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if isinstance(value,libxml2.xmlNode):
			self.uri,self.sound,self.phonetic=[None]*3
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
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
				n=n.next
			if (not self.phonetic and not self.image and not self.sound):
				raise Empty,"Bad SOUND value in vcard"
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
		ns=get_node_ns(parent)
		n=parent.newChild(ns,self.name.upper(),None)
		if self.uri:
			n.newTextChild(ns,"EXTVAL",to_utf8(self.uri))
		elif self.phonetic:
			n.newTextChild(ns,"PHONETIC",to_utf8(self.phonetic))
		else:
			n.newTextChild(ns,"BINVAL",binascii.b2a_base64(self.image))
		return n

class VCardPrivacy:
	def __init__(self,name,value,rfc2425parameters={}):
		if isinstance(value,libxml2.xmlNode):
			self.value=None
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
					continue
				if n.name=='PUBLIC':
					self.value="public"
				elif n.name=='PRIVATE':
					self.value="private"
				elif n.name=='CONFIDENTAL':
					self.value="confidental"
				n=n.next
			if not self.value:
				raise Empty
		else:
			self.value=value
	def rfc2426(self):
		return rfc2425encode(self.name,self.value)
	def xml(self,parent):
		ns=get_node_ns(parent)
		if self.value in ("public","private","confidental"):
			n=parent.newChild(ns,self.name.upper(),None)
			n.newChild(ns,self.value.upper(),None)
			return n
		return None

class VCardKey:
	def __init__(self,name,value,rfc2425parameters={}):
		self.name=name
		if isinstance(value,libxml2.xmlNode):
			self.type,self.cred=None,None
			n=value.children
			vns=get_node_ns(value)
			while n:
				if n.type!='element':
					n=n.next
					continue
				ns=get_node_ns(n)
				if (ns and vns and ns.getContent()!=vns.getContent()):
					n=n.next
					continue
				if n.name=='TYPE':
					self.type=unicode(n.getContent(),"utf-8","replace")
				if n.name=='CRED':
					self.sound=base64.decodestring(n.getContent())
				n=n.next
			if not self.cred:
				raise Empty,"Bad %s value in vcard" % (name,)
		else:
			self.type=rfc2425parameters.get("type")
			self.cred=value
	def rfc2426(self):
		if self.type:
			p={"type":self.type}
		else:
			p={}
		return rfc2425encode(self.name,self.cred,p)
	def xml(self,parent):
		ns=get_node_ns(parent)
		n=parent.newChild(ns,self.name.upper(),None)
		if self.type:
			n.newTextChild(ns,"TYPE",self.type)
		n.newTextChild(ns,"CRED",binascii.b2a_base64(self.key))
		return n

class VCard:
	components={
			#"VERSION": (VCardString,"optional"),
			"FN": (VCardString,"required"),
			"N": (VCardName,"required"),
			"NICKNAME": (VCardString,"multi"),
			"PHOTO": (VCardImage,"multi"),
			"BDAY": (VCardString,"multi"),
			"ADR": (VCardAdr,"multi"),
			"LABEL": (VCardLabel,"multi"),
			"TEL": (VCardTel,"multi"),
			"EMAIL": (VCardEmail,"multi"),
			"JABBERID": (VCardJID,"multi"),
			"MAILER": (VCardString,"multi"),
			"TZ": (VCardString,"multi"),
			"GEO": (VCardGeo,"multi"),
			"TITLE": (VCardString,"multi"),
			"ROLE": (VCardString,"multi"),
			"LOGO": (VCardImage,"multi"),
			"AGENT": ("VCardAgent","ignore"), #FIXME#
			"ORG": (VCardOrg,"multi"),
			"CATEGORIES": (VCardCategories,"multi"),
			"NOTE": (VCardString,"multi"),
			"PRODID": (VCardString,"multi"),
			"REV": (VCardString,"multi"),
			"SORT-STRING": (VCardString,"multi"),
			"SOUND": (VCardSound,"multi"),
			"UID": (VCardString,"multi"),
			"URL": (VCardString,"multi"),
			"CLASS": (VCardString,"multi"),
			"KEY": (VCardKey,"multi"),
			"DESC": (VCardXString,"multi"),
		};
	def __init__(self,data):
		self.content={}
		if isinstance(data,libxml2.xmlNode):
			ns=get_node_ns(data)
			if ns and ns.getContent()!="vcard-temp":
				raise ValueError,"Not in the 'vcard-temp' namespace"
			if data.name!="vCard":
				raise ValueError,"Bad root element name: %r" % (data.name,)
			n=data.children
			dns=get_node_ns(data)
			while n:
				if n.type!='element':
					n=n.next
					continue
				print "element:",`n.name`
				ns=get_node_ns(n)
				if ns:
					print "namespace:",`ns.getContent()`
				else:
					print "no namespace"
				if (ns and dns and ns.getContent()!=dns.getContent()):
					n=n.next
					continue
				if not self.components.has_key(n.name):
					n=n.next
					continue
				cl,tp=self.components[n.name]
				if tp in ("required","optional"):
					if self.content.has_key(n.name):
						raise ValueError,"Duplicate %s" % (n.name,)
					try:
						self.content[n.name]=cl(n.name,n)
					except Empty:
						pass
				elif tp=="multi":
					if not self.content.has_key(n.name):
						self.content[n.name]=[]
					try:
						self.content[n.name].append(cl(n.name,n))
					except Empty:
						pass
				n=n.next
		else:
			data=from_utf8(data)
			lines=data.split("\n")
			started=0
			current=None
			for l in lines:
				if not l:
					continue
				if l[-1]=="\r":
					l=l[:-1]
				if l[0] in " \t":
					if current is None:
						continue
					current+=l[1:]
					continue
				if not started and current and current.upper().strip()=="BEGIN:VCARD":
					started=1
				elif started and current.upper().strip()=="END:VCARD":
					current=None
					break
				elif current and started:
					self.process_rfc2425_record(current)
				current=l
			if started and current:
				self.process_rfc2425_record(current)
		for c,(cl,tp) in self.components.items():
			if self.content.has_key(c):
				continue
			if tp=="required":
				raise ValueError,"%s is missing" % (c,)
			elif tp=="multi":
				self.content[c]=[]
			elif tp=="optional":
				self.content[c]=None
			else:
				continue

	def process_rfc2425_record(self,data):
		label,value=data.split(":",1)
		psplit=label.split(";")
		name=psplit[0]
		params=psplit[1:]
		if u"." in name:
			group,name=name.split(".",1)
		name=name.upper()
		if name in (u"X-DESC",u"X-JABBERID"):
			name=name[2:]
		if not self.components.has_key(name):
			return
		if params:
			params=dict([p.split("=",1) for p in params])
		cl,tp=self.components[name]
		if tp in ("required","optional"):
			if self.content.has_key(name):
				raise ValueError,"Duplicate %s" % (name,)
			try:
				self.content[name]=cl(name,value,params)
			except Empty:
				pass
		elif tp=="multi":
			if not self.content.has_key(name):
				self.content[name]=[]
			try:
				self.content[name].append(cl(name,value,params))
			except Empty:
				pass
		else:
			return
	def __repr__(self):
		return "<vCard of %r>" % (self.content["FN"].value,)
	def rfc2426(self):
		ret="begin:VCARD\r\n"
		ret+="version:3.0\r\n"
		for name,value in self.content.items():
			if value is None:
				continue
			if type(value) is types.ListType:
				for v in value:
					ret+=v.rfc2426()
			else:
				ret+=value.rfc2426()
		return ret+"end:VCARD\r\n"
