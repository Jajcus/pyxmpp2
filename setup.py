#! /usr/bin/env python
# $Id: setup.py,v 1.1 2003/06/03 12:50:43 jajcus Exp $

from distutils.core import setup, Extension

#-- Let distutils do the rest
setup(
	#-- Package description
	name =		'pyxmpp',
	version =	'0.0',
	description =	'XMPP implementation for Python',
	author =	'Jacek Konieczny', 
	author_email =	'jajcus@bnet.pl',
	url =		'http://pyxmpp.jabberstudio.org/',
	license =	'LGPL',
	ext_modules = [
		Extension(
		    'pyxmpp._libxml2addon',
		    [
			'libxml2addon/xmlreader.c',
			'libxml2addon/tree.c',
			'libxml2addon/libxml.c',
			'libxml2addon/types.c',
			'libxml2addon/libxml2-py.c',
		    ],
		    libraries =		['xml2'],
		    include_dirs =	['libxml2addon','/usr/include/libxml2'],
		),
	],
	#-- Python modules
	py_modules = [
                'pyxmpp.client',
                'pyxmpp.error',
		'pyxmpp.expdict',
		'pyxmpp.iq',
		'pyxmpp.jid',
		'pyxmpp.message',
		'pyxmpp.presence',
		'pyxmpp.stanza',
		'pyxmpp.stream',
		'pyxmpp.utils',
		'pyxmpp.libxml2addon',
		'pyxmpp.sasl.core',
		'pyxmpp.sasl.plain',
		'pyxmpp.sasl.digest_md5',
	],
	#-- where to find the python modules
	package_dir = { 'pyxmpp': '.' },
)

