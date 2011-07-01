#! /usr/bin/env python

import os.path
import sys

version = "1.99.0-git"

if (not os.path.exists(os.path.join("pyxmpp2","version.py"))
                                    or "make_version" in sys.argv):
    with open("pyxmpp2/version.py", "w") as version_py:
        version_py.write("# pylint: disable=C0111,C0103\n")
        version_py.write("version = {0!r}\n".format(version))
    if "make_version" in sys.argv:
        sys.exit(0)
else:
    execfile(os.path.join("pyxmpp2", "version.py"))
    
    
if version.endswith("-git"):
    download_url = None
else:
    download_url = 'http://github.com/downloads/Jajcus/pyxmpp2/pyxmpp2-{0}.tar.gz'.format(version),

from distutils.core import setup

setup(
    name =      'pyxmpp2',
    version =   version,
    description =   'XMPP/Jabber implementation for Python',
    author =    'Jacek Konieczny',
    author_email =  'jajcus@jajcus.net',
    download_url = download_url,
    url =       'https://github.com/Jajcus/pyxmpp2',
    classifiers = [
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
            "Operating System :: POSIX",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2.7",
            "Topic :: Communications",
            "Topic :: Communications :: Chat",
            "Topic :: Internet",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    license =   'LGPL',
    requires = ['dnspython(>= 1.6.0)'],
    packages = [
        'pyxmpp2',
        'pyxmpp2.mainloop',
        'pyxmpp2.sasl',
    #   'pyxmpp2.ext',
    ],
)
