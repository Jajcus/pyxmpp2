#! /usr/bin/env python
# $Id: setup.py,v 1.14 2004/06/02 21:20:16 jajcus Exp $

import os.path
import sys

if sys.hexversion<0x02030000:
    raise ImportError,"Python 2.3 or newer is required"

if not os.path.exists(os.path.join("pyxmpp","version.py")):
    print >>sys.stderr,"You need to run 'make' to use pyxmpp from SVN"
    sys.exit(1)

execfile(os.path.join("pyxmpp","version.py"))

from distutils.core import setup, Extension

#-- Let distutils do the rest
setup(
    #-- Package description
    name =      'pyxmpp',
    version =   version,
    description =   'XMPP/Jabber implementation for Python',
    author =    'Jacek Konieczny',
    author_email =  'jajcus@bnet.pl',
    url =       'http://pyxmpp.jabberstudio.org/',
    classifiers = [
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
            "Operating System :: POSIX",
            "Programming Language :: Python",
            "Programming Language :: C",
            "Topic :: Communications",
            "Topic :: Communications :: Chat",
            "Topic :: Internet",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    license =   'LGPL',
    ext_modules = [
        Extension(
            'pyxmpp._xmlextra',
            [
            'ext/xmlextra.c',
            ],
            libraries =     ['xml2'],
            include_dirs =  ['libxml2addon','/usr/include/libxml2','/usr/local/include/libxml2'],
            extra_compile_args = ['-g2'],
        ),
    ],
    #-- Python modules
    packages = [
        'pyxmpp',
        'pyxmpp.jabber',
        'pyxmpp.jabberd',
        'pyxmpp.sasl',
    ],
)

# vi: sts=4 et sw=4
