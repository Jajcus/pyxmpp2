#! /usr/bin/env python

import os.path
import sys

if not os.path.exists(os.path.join("pyxmpp","version.py")):
    print >>sys.stderr,"You need to run 'make' to use pyxmpp from SVN"
    sys.exit(1)

execfile("build.cfg")
execfile(os.path.join("pyxmpp", "version.py"))

from distutils.core import setup, Extension

if python_only:
    ext_modules = None
else:
    # set reasonable defaults, just in case
    if sys.platform == 'win32':
        include_dirs = [r'd:\libs\include', r'd:\libs\include\libxml']
        library_dirs = [r'd:\libs\lib']
    else:
        include_dirs = ['/usr/include/libxml2','/usr/local/include/libxml2']
        library_dirs = []


#-- Let distutils do the rest
setup(
    #-- Package description
    name =      'pyxmpp2',
    version =   version,
    description =   'XMPP/Jabber implementation for Python',
    author =    'Jacek Konieczny',
    author_email =  'jajcus@jajcus.net',
    download_url = 'https://github.com/downloads/Jajcus/pyxmpp2/pyxmpp-{0}.tar.gz'.format(version),
    url =       'http://pyxmpp.jajcus.net/',
    classifiers = [
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
            "Operating System :: POSIX",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2.6",
            "Programming Language :: C",
            "Topic :: Communications",
            "Topic :: Communications :: Chat",
            "Topic :: Internet",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    license =   'LGPL',
    requires = ['dnspython(>= 1.6.0)'],
    package_dir = {'pyxmpp2': 'pyxmpp'},
    #-- Python modules
    packages = [
        'pyxmpp2',
        'pyxmpp2.mainloop',
#        'pyxmpp2.jabber',
#        'pyxmpp2.jabberd',
        'pyxmpp2.sasl',
    ],
)

# vi: sts=4 et sw=4
