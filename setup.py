#! /usr/bin/env python

import os.path
import sys

from setuptools import setup

version = "2.0.1"

if (not os.path.exists(os.path.join("pyxmpp2","version.py"))
                                    or "make_version" in sys.argv):
    with open("pyxmpp2/version.py", "w") as version_py:
        version_py.write("# pylint: disable=C0111,C0103\n")
        version_py.write("version = {0!r}\n".format(version))
    if "make_version" in sys.argv:
        sys.exit(0)
else:
    exec(open(os.path.join("pyxmpp2", "version.py")).read())


if version.endswith("-git"):
    download_url = None
else:
    download_url = 'http://github.com/downloads/Jajcus/pyxmpp2/pyxmpp2-{0}.tar.gz'.format(version),


extra = {}
if sys.version_info[0] >= 3:
    extra['use_2to3'] = True
    extra['use_2to3_fixers'] = ['custom_2to3']
    install_requires = []
else:
    install_requires = ['dnspython >=1.6.0']

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
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.3",
            "Programming Language :: Python :: 3.4",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Topic :: Communications",
            "Topic :: Communications :: Chat",
            "Topic :: Internet",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    license =   'LGPL',
    install_requires = install_requires,
    packages = [
        'pyxmpp2',
        'pyxmpp2.mainloop',
        'pyxmpp2.sasl',
        'pyxmpp2.ext',
        'pyxmpp2.server',
        'pyxmpp2.test',
    ],
    package_data = {
        'pyxmpp2.test': ['data/*.pem', 'data/*.txt', 'data/*.xml'],
    },
    test_suite = "pyxmpp2.test.discover",
    **extra
)
