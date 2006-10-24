#!/usr/bin/env python

import sys
import os


cfg_python_only = False

d = os.path.dirname(__file__)
if not d:
    d = "."
os.chdir(d)

print "Checking for python version...", sys.version.replace("\n", " ")
if sys.hexversion < 0x02030000:
    print >>sys.stderr, "ERROR: Python 2.3 or newer is required"
    sys.exit(1)

print "Checking for dnspython...",
try:
    import dns.resolver
    import dns.version
except ImportError:
    print "not found"
    print >>sys.stderr, "ERROR: You need dnspython from http://www.dnspython.org/"
    sys.exit(1)
print "version %s found" % (dns.version.version,)

print "Checking for libxml2 python bindings...",
try:
    import libxml2
except ImportError:
    print "not found"
    print >>sys.stderr, "ERROR: You need libxml2 python bindings for PyXMPP"
    sys.exit(1)
print "found"
    
print "Checking for M2Crypto...",
try:
    from M2Crypto import SSL
    from M2Crypto.SSL import SSLError
    import M2Crypto.SSL.cb
    print "version %s found. Hope it will work." % (M2Crypto.version,)
except ImportError:
    print "not found"
    print >>sys.stderr, "Warning: You need M2Crypto (some good version) for StartTLS support in PyXMPP"

print "Trying to build the binary extension...",
build_cfg = file("build.cfg", "w")
print >>build_cfg, "python_only = False"
build_cfg.close()
try:
    os.system("python setup.py clean --all >/dev/null 2>&1")
    ret = os.system("python setup.py build_ext >build_test.log 2>&1")
except OSError:
    ret = -1
if ret:
    print "failed"
    print >>sys.stderr, "Warning: Couldn't build the binary extension. Python or libxml2 devel files are missing. Will use python-only implementation."
    print >>sys.stderr, "See build_test.log file for failure details."
    cfg_python_only = True
else:
    print "success"
    os.unlink("build_test.log")
    cfg_python_only = False

# Write build.cfg

build_cfg = file("build.cfg", "w")
print >>build_cfg, "python_only =", cfg_python_only
build_cfg.close()

print
print "Configuration successfull"
print "You may now build pyxmpp with 'python setup.py build'"
print "and install it with 'python setup.py install'"
