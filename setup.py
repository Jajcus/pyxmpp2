#! /usr/bin/env python
# $Id: setup.py,v 1.4 2003/06/06 10:15:24 jajcus Exp $

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
		    'pyxmpp._xmlextra',
		    [
			'ext/xmlextra.c',
		    ],
		    libraries =		['xml2'],
		    include_dirs =	['libxml2addon','/usr/include/libxml2'],
		    extra_compile_args = ['-g2'],
		),

	],
	#-- Python modules
	packages = [
                'pyxmpp',
		'pyxmpp.sasl',
	],
)

