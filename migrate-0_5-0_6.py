#!/usr/bin/python

import sys
import re
import os

args=sys.argv[1:]
if not args or "-h" in args or "--help" in args:
    print "PyXMPP 0.5 to 0.6 code updater."
    print "Usage:"
    print "    %s file..." % (sys.argv[0],)
    print
    print "This script will try to update your code for the recent changes"
    print "in the PyXMPP package. But this updates are just simple regexp"
    print "substitutions which may _break_ your code. Always check the result."
    sys.exit(0)


in_par=r"(?:\([^)]*\)|[^()])"


updates=[
    (r"(\b(?:Muc)?(?:Stanza|Message|Iq|Presence)\("+in_par+r"*)\bfr=("+in_par+r"+\))",r"\1from_jid=\2"),
    (r"(\b(?:Muc)?(?:Stanza|Message|Iq|Presence)\("+in_par+r"*)\bto=("+in_par+r"+\))",r"\1to_jid=\2"),
    (r"(\b(?:Muc)?(?:Stanza|Message|Iq|Presence)\("+in_par+r"*)\btype?=("+in_par+r"+\))",r"\1stanza_type=\2"),
    (r"(\b(?:Muc)?(?:Stanza|Message|Iq|Presence)\("+in_par+r"*)\bs?id=("+in_par+r"+\))",r"\1stanza_id=\2"),
    ]

updates=[(re.compile(u_re,re.MULTILINE|re.DOTALL),u_repl)
            for u_re,u_repl in updates]

for fn in args:
    print fn+":",
    orig_code=file(fn).read()
    changes_made=0
    code=orig_code
    for u_re,u_repl in updates:
        (code,cm)=u_re.subn(u_repl,code)
        changes_made+=cm
    if changes_made:
        print changes_made,"changes"
        os.rename(fn,fn+".bak")
        file(fn,"w").write(code)
    else:
        print "no changes"


# vi: sts=4 et sw=4
