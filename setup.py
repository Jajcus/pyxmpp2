#! /usr/bin/env python
# $Id: setup.py,v 1.7 2003/08/15 15:51:46 jajcus Exp $

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
		    include_dirs =	['libxml2addon','/usr/include/libxml2'],
		    extra_compile_args = ['-g2'],
		),

	],
	#-- Python modules
	packages = [
                'pyxmpp',
		'pyxmpp.sasl',
		'pyxmpp.unicode',
	],
)

