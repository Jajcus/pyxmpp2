#! /usr/bin/env python
# $Id: setup.py,v 1.2 2003/06/04 12:08:35 jajcus Exp $

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
		    'pyxmpp.libxml2addon._libxml2addon',
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
	packages = [
                'pyxmpp',
		'pyxmpp.libxml2addon',
		'pyxmpp.sasl',
	],
)

