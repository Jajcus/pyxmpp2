#! /usr/bin/env python
# $Id: setup.py,v 1.9 2003/11/30 17:06:15 jajcus Exp $

import os.path
import sys

if not os.path.exists(os.path.join("pyxmpp","version.py")):
	print >>sys.stderr,"You need to run 'make' to use pyxmpp from CVS"
	sys.exit(1)

execfile(os.path.join("pyxmpp","version.py"))

from distutils.core import setup, Extension

#-- Let distutils do the rest
setup(
	#-- Package description
	name =		'pyxmpp',
	version =	version,
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
		    include_dirs =	['libxml2addon','/usr/include/libxml2','/usr/local/include/libxml2'],
		    extra_compile_args = ['-g2'],
		),

	],
	#-- Python modules
	packages = [
                'pyxmpp',
                'pyxmpp.jabber',
		'pyxmpp.sasl',
		'pyxmpp.unicode',
	],
)

